# -*- coding: utf-8 -*-
import os
import sqlite3
import subprocess
import requests
import time
import random
import re
import json
from datetime import datetime
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

# ================= 1. 加载机密引擎配置 =================
script_dir = os.path.dirname(os.path.abspath(__file__))
env_local = os.path.join(script_dir, ".env")
env_vps = "/root/scripts/.env"
if os.path.exists(env_local):
    load_dotenv(env_local)
elif os.path.exists(env_vps):
    load_dotenv(env_vps)
DB_FILE = os.getenv("DB_FILE")
PAGE_DIR = os.getenv("PAGE_DIR")
INDEX_FILE = os.getenv("INDEX_FILE")
SITEMAP_FILE = os.getenv("SITEMAP_FILE")
NGINX_CONF_FILE = os.getenv("NGINX_CONF_FILE")
DOMAIN = os.getenv("DOMAIN")
BAIDU_TOKEN = os.getenv("BAIDU_TOKEN")
DAILY_QUOTA = int(os.getenv("DAILY_PUSH_QUOTA", 100))
PUSHED_LOG_FILE = os.getenv("PUSHED_LOG_FILE")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
CLARITY_ID = os.getenv("CLARITY_ID")

os.makedirs(PAGE_DIR, exist_ok=True)

# 初始化 Jinja2 模板引擎
_template_dir = os.path.join(script_dir, "templates")
if not os.path.isdir(_template_dir):
    _template_dir = "/root/scripts/templates"
env = Environment(loader=FileSystemLoader(_template_dir))
detail_template = env.get_template('detail.html')
list_template = env.get_template('list.html')
transit_template = env.get_template('transit.html') # ✅ 包含了第二步的中转页模板

# ================= 2. 智能网盘识别引擎 (Regex 安全升级版) =================
def identify_drive(url):
    """网盘智能识别引擎：采用严格正则边界匹配，防止伪造域名投毒"""
    if not url: return "极速转存"
    url = str(url).lower()
    
    # 工业级正则匹配字典
    drive_patterns = {
        r'(?:^|[\./])quark\.cn(?:/|$)': "夸克网盘",
        r'(?:^|[\./])baidu\.com(?:/|$)': "百度网盘",
        r'(?:^|[\./])(alipan\.com|aliyundrive\.com)(?:/|$)': "阿里云盘",
        r'(?:^|[\./])xunlei\.com(?:/|$)': "迅雷网盘",
        r'(?:^|[\./])123pan\.(com|cn)(?:/|$)': "123网盘",
        r'(?:^|[\./])189\.cn(?:/|$)': "天翼云盘",
        r'(?:^|[\./])lanzou[a-z0-9]?(?:\.com|\.net|\.cn)(?:/|$)': "蓝奏云", 
        r'(?:^|[\./])115\.com(?:/|$)': "115网盘",
        r'(?:^|[\./])uc\.cn(?:/|$)': "UC网盘",
        r'(?:^|[\./])weiyun\.com(?:/|$)': "腾讯微云",
        r'(?:^|[\./])ctfile\.com(?:/|$)': "诚通网盘",
        r'(?:^|[\./])10086\.cn(?:/|$)': "移动云盘"
    }

    for pattern, name in drive_patterns.items():
        if re.search(pattern, url):
            return name
            
    return "专属专线"

def fetch_data_from_db():
    """从 SQLite 极速拉取数据"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM resources ORDER BY res_id ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

# ================= 3. 柔性安全防线 (Nginx 更新) =================
def safe_update_nginx(resources):
    """写入规则前执行语法检查，防止 Nginx 宕机"""
    print("🛡️ 正在进行 Nginx 柔性热更新...")
    rules = ""
    for res in resources:
        if res.get('normal_url'): rules += f"rewrite ^/jump/{res['res_id']}$ {res['normal_url']} redirect;\n"
        if res.get('short_url'): rules += f"rewrite ^/jump/{res['res_id']}_short$ {res['short_url']} redirect;\n"

    tmp_file = NGINX_CONF_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write(rules)

    # 物理级语法预检
    result = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
    if "syntax is ok" in result.stderr.lower():
        os.replace(tmp_file, NGINX_CONF_FILE)
        subprocess.run(["nginx", "-s", "reload"])
        print("✅ Nginx 语法检查通过，底层路由规则已无缝重载！")
    else:
        print(f"❌ [致命拦截] 发现 Nginx 语法错误，已阻止危险覆写！报错信息:\n{result.stderr}")
        if os.path.exists(tmp_file): os.remove(tmp_file)

# ================= 4. 高并发渲染引擎 =================
def render_single_page(res):
    """渲染单一静态页的微进程"""
    # 动态附加网盘名称
    res['drive_name'] = identify_drive(res.get('short_url') or res.get('normal_url'))
    
    # ✅ 1. 生成详情页 (新增了 related_resources 参数，完成第三步内部蜘蛛网注入)
    html_content = detail_template.render(
        title=res['title'], seo_desc=res['seo_desc'], size=res['size'],
        res_id=res['res_id'], normal_url=res.get('normal_url'), short_url=res.get('short_url'),
        drive_name=res['drive_name'], admin_email=ADMIN_EMAIL, clarity_id=CLARITY_ID,
        canonical_url=f"{DOMAIN}/go/{res['res_id']}",
        related_resources=res.get('related', []),
        category=res.get('category'), platform=res.get('platform'),
        version=res.get('version'), password=res.get('password'), rating=res.get('rating'),
        ai_generated=res.get('ai_generated', False)
    )
    with open(os.path.join(PAGE_DIR, f"{res['res_id']}.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

    # ✅ 2. 生成普通链接的中转页 (如果存在)
    if res.get('normal_url'):
        transit_html = transit_template.render(
            title=res['title'], jump_id=res['res_id'],
            admin_email=ADMIN_EMAIL, clarity_id=CLARITY_ID,
            canonical_url=f"{DOMAIN}/go/{res['res_id']}"
        )
        with open(os.path.join(PAGE_DIR, f"{res['res_id']}_transit.html"), "w", encoding="utf-8") as f:
            f.write(transit_html)

    # ✅ 3. 生成短链极速版的中转页 (如果存在)
    if res.get('short_url'):
        transit_html_short = transit_template.render(
            title=res['title'], jump_id=f"{res['res_id']}_short",
            admin_email=ADMIN_EMAIL, clarity_id=CLARITY_ID,
            canonical_url=f"{DOMAIN}/go/{res['res_id']}"
        )
        with open(os.path.join(PAGE_DIR, f"{res['res_id']}_short_transit.html"), "w", encoding="utf-8") as f:
            f.write(transit_html_short)

def build_static_site(resources):
    """多线程并发生成全站"""
    print(f"⚡ 启动多线程并发渲染引擎，目标: {len(resources)} 个独立页面与倒计时中转页...")
    
    # ✅ 织网行动：为每个资源随机注入 4 个“猜你喜欢”的内链
    for res in resources:
        candidates = [r for r in resources if r['res_id'] != res['res_id']]
        # 如果总资源大于4个，就随机抽4个；不够就全拿
        res['related'] = random.sample(candidates, min(4, len(candidates)))
    
    # 1. 多线程并发生成独立详情页与中转页
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(render_single_page, resources)
    
    # 2. 生成独立 index.json (异步拉取 + Preload 预加载)
    web_root = os.path.dirname(INDEX_FILE)  # var/www/site/web
    json_rows = []
    for res in resources:
        json_rows.append({
            'id': res['res_id'],
            'title': res['title'],
            'size': res.get('size', '-'),
            'category': res.get('category', ''),
            'drive': identify_drive(res.get('short_url') or res.get('normal_url'))
        })
    json_path = os.path.join(web_root, 'index.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_rows, f, ensure_ascii=False)
    print(f"  index.json: {len(json_rows)} 条资源, {os.path.getsize(json_path)//1024}KB")

    list_html = list_template.render(
        resources=resources,
        admin_email=ADMIN_EMAIL, clarity_id=CLARITY_ID
    )
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(list_html)

    # 3. 生成分类标签页
    categories = Counter(r.get('category') for r in resources if r.get('category'))
    if categories:
        tag_dir = os.path.join(os.path.dirname(INDEX_FILE))
        for cat, count in categories.most_common():
            cat_slug = cat.strip().lower().replace(' ', '_').replace('/', '_')
            cat_resources = [r for r in resources if r.get('category', '').strip() == cat.strip()]
            tag_html = list_template.render(
                resources=cat_resources,
                admin_email=ADMIN_EMAIL, clarity_id=CLARITY_ID,
                filter_category=cat
            )
            tag_path = os.path.join(tag_dir, f'tag_{cat_slug}.html')
            with open(tag_path, 'w', encoding='utf-8') as f:
                f.write(tag_html)
            print(f"  🏷 {cat}: {count} 条 → {tag_path}")

    print("✅ 全站纯静态 HTML 矩阵生成完毕！(已注入 5 秒防刷与内链蜘蛛网)")

# ================= 4b. 合集/专题页面 (P1-3) =================
def fetch_collections_from_db():
    """从 SQLite 读取合集+关联资源，返回结构化列表."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    colls = cursor.execute("""
        SELECT c.id, c.title, c.is_featured,
               cc.intro, cc.seo_title, cc.seo_desc, cc.faq_json,
               cc.editor_note, cc.why_collect, cc.audience, cc.highlights
        FROM collections c
        LEFT JOIN collection_content cc ON c.id = cc.collection_id
        ORDER BY c.sort_order
    """).fetchall()
    result = []
    for coll in colls:
        res_rows = cursor.execute("""
            SELECT r.* FROM resources r
            JOIN resource_collections rc ON r.res_id = rc.resource_id
            WHERE rc.collection_id = ?
            ORDER BY rc.score DESC
        """, (coll["id"],)).fetchall()
        if res_rows:
            result.append({"coll": dict(coll), "resources": [dict(r) for r in res_rows]})
    conn.close()
    return result


def build_collection_pages():
    """为每个合集生成独立专题页 (collection.html 模板)."""
    collections = fetch_collections_from_db()
    if not collections:
        print("  📭 无合集数据，跳过专题页")
        return []

    from jinja2 import Environment, FileSystemLoader
    coll_template = Environment(loader=FileSystemLoader(_template_dir)).get_template('collection.html')
    web_root = os.path.dirname(INDEX_FILE)
    coll_dir = os.path.join(web_root, "collection")
    os.makedirs(coll_dir, exist_ok=True)
    coll_urls = []

    for item in collections:
        coll = item["coll"]
        coll_res = item["resources"]
        slug = coll["id"]

        faq_json = coll.get("faq_json", "")
        faq_list = json.loads(faq_json) if faq_json else []

        # Schema.org: CollectionPage + BreadcrumbList + ItemList + FAQPage
        coll_url = f"{DOMAIN}/collection/{slug}.html"
        schema_graph = [
            {"@type":"CollectionPage","@id":coll_url,"url":coll_url,
             "name":coll["title"],
             "description":coll.get("seo_desc") or coll.get("intro",""),
             "isPartOf":{"@type":"WebSite","name":"BigPRC","url":DOMAIN},
             "about":{"@type":"Thing","name":coll["title"]},
             "mainEntity":{"@type":"ItemList",
                "name":f"{coll['title']}精选资源",
                "numberOfItems":len(coll_res),
                "itemListElement":[{"@type":"ListItem","position":i+1,"url":f"{DOMAIN}/go/{r['res_id']}"}
                                   for i,r in enumerate(coll_res[:20])]}},
            {"@type":"BreadcrumbList",
             "itemListElement":[
                 {"@type":"ListItem","position":1,"name":"BigPRC","item":DOMAIN},
                 {"@type":"ListItem","position":2,"name":"精选专题","item":f"{DOMAIN}/collection/index.html"},
                 {"@type":"ListItem","position":3,"name":coll["title"],"item":coll_url}]}
        ]
        if faq_list:
            schema_graph.append({"@type":"FAQPage",
                "mainEntity":[{"@type":"Question","name":item["q"],
                               "acceptedAnswer":{"@type":"Answer","text":item["a"]}}
                              for item in faq_list]})
        schema_json = json.dumps({"@context":"https://schema.org","@graph":schema_graph}, ensure_ascii=False)

        html = coll_template.render(
            resources=coll_res,
            coll_title=coll["title"],
            coll_intro=coll.get("intro", ""),
            seo_title=coll.get("seo_title", ""),
            seo_desc=coll.get("seo_desc", ""),
            faq_html=faq_list,
            editor_note=coll.get("editor_note", ""),
            why_collect=coll.get("why_collect", ""),
            audience=coll.get("audience", ""),
            highlights=json.loads(coll.get("highlights", "[]")) if coll.get("highlights") else [],
            schema_json=schema_json,
            admin_email=ADMIN_EMAIL, clarity_id=CLARITY_ID
        )
        path = os.path.join(coll_dir, f"{slug}.html")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        coll_urls.append(f"/collection/{slug}.html")
        print(f"  📚 {coll['title']}: {len(coll_res)} 条 → {path}")

    # 生成专题索引页
    idx_template = Environment(loader=FileSystemLoader(_template_dir)).get_template('collection_index.html')
    idx_data = [{"id": c["id"], "title": c["title"], "intro": c.get("intro",""),
                 "count": len(r["resources"]), "featured": c.get("is_featured",0)}
                for c, r in [(item["coll"], item) for item in collections]]
    idx_html = idx_template.render(collections=idx_data, admin_email=ADMIN_EMAIL, clarity_id=CLARITY_ID)
    idx_path = os.path.join(coll_dir, "index.html")
    with open(idx_path, 'w', encoding='utf-8') as f:
        f.write(idx_html)
    coll_urls.append("/collection/index.html")
    print(f"  📚 专题索引页: {len(idx_data)} 个专题 → {idx_path}")

    # 生成 collections.json 供首页 JS 渲染
    json_path = os.path.join(web_root, "collections.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(idx_data, f, ensure_ascii=False)
    print(f"  collections.json: {len(idx_data)} 专题, {os.path.getsize(json_path)}B")

    print(f"✅ {len(coll_urls)} 个专题页生成完毕")
    return coll_urls


# ================= 5. SEO 地图与 API 推送 =================
def generate_sitemap(resources, coll_urls=None):
    """生成 XML 地图 (含合集页面)."""
    print("🗺️ 正在生成 XML 网站地图...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    urls = [f"<url><loc>{DOMAIN}/</loc><lastmod>{current_date}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>"]
    for res in resources:
        urls.append(f"<url><loc>{DOMAIN}/go/{res['res_id']}</loc><lastmod>{current_date}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>")
    if coll_urls:
        for u in coll_urls:
            urls.append(f"<url><loc>{DOMAIN}{u}</loc><lastmod>{current_date}</lastmod><changefreq>daily</changefreq><priority>0.9</priority></url>")

    sitemap_content = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n    {"".join(urls)}\n</urlset>'
    with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
        f.write(sitemap_content)

def smart_push_engine(resources):
    """百度防封推送引擎 (读取数据库并限流)"""
    def load_pushed():
        if os.path.exists(PUSHED_LOG_FILE):
            with open(PUSHED_LOG_FILE, 'r') as f: return set(f.read().splitlines())
        return set()
        
    pushed_set = load_pushed()
    api_url = f"http://data.zz.baidu.com/urls?site={DOMAIN}&token={BAIDU_TOKEN}"
    
    target_urls = [f"{DOMAIN}/", f"{DOMAIN}/list.html"] + [f"{DOMAIN}/go/{r['res_id']}" for r in resources]
    unpushed_urls = [u for u in target_urls if u not in pushed_set]
    
    if not unpushed_urls:
        print("\n📭 [状态监控] 当前库中所有优质页面均已推送过，API 引擎进入休眠。")
        return

    push_list = unpushed_urls[:DAILY_QUOTA]
    print(f"\n🚀 [智能调度] 发现 {len(unpushed_urls)} 条未推送新资源，本次安全提取 {len(push_list)} 条传输...")
    
    success_total = 0
    for i in range(0, len(push_list), 20):
        batch = push_list[i:i + 20]
        if i > 0: time.sleep(random.uniform(3.5, 7.5))
        
        try:
            response = requests.post(api_url, data="\n".join(batch), headers={'Content-Type': 'text/plain'}, timeout=15)
            result = response.json()
            if 'success' in result:
                success_total += result['success']
                with open(PUSHED_LOG_FILE, 'a') as f:
                    for u in batch: f.write(f"{u}\n")
                print(f"   ✅ 批次吞吐成功！剩余额度: {result.get('remain')}")
            else:
                print(f"   🛑 [熔断触发] {result.get('message')}。引擎强制拉闸，保护账号！")
                break
        except Exception as e:
            print(f"   💥 网络物理级断裂: {e}")
            break
    print(f"🏁 今日推送结束，成功护送 {success_total} 条。")

# ================= 🚀 主程序引擎启动 =================
if __name__ == "__main__":
    start_time = time.time()
    
    data = fetch_data_from_db()
    if not data:
        print("⚠️ 数据库为空，请先运行 pantools_sync.py 导入数据！")
        exit()
        
    build_static_site(data)
    coll_urls = build_collection_pages()
    try:
        safe_update_nginx(data)
    except Exception as e:
        print(f"[SKIP] Nginx update skipped (local/dev environment): {e}")
    generate_sitemap(data, coll_urls)
    try:
        smart_push_engine(data)
    except Exception as e:
        print(f"[SKIP] Baidu push skipped (local/dev environment): {e}")
    
    print(f"\n🎉 极客引擎全链路执行完毕！总耗时: {time.time() - start_time:.2f} 秒")