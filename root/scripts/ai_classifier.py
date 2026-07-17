#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC ai_classifier.py — AI 资源分类器 (P0-B.2.5)

输入: resources.title + resources.seo_desc (已有 1760 条 SEO 描述)
输出: resources.category, resources.platform
      resource_content.resource_type (media/software/course/book/game/website/tool/other)

用法:
  python3 ai_classifier.py --plan          # 统计待分类数量
  python3 ai_classifier.py --limit 10      # 灰度测试
  python3 ai_classifier.py                 # 全量分类
  python3 ai_classifier.py --force         # 覆盖已有分类

Config: 读取 /root/scripts/.env (DB_FILE, API_BASE_URL, API_KEY)
"""

import os
import sys
import json
import time
import sqlite3
import argparse
from dotenv import load_dotenv
from openai import OpenAI

# ============================================================
# 1. 配置
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY      = os.getenv("API_KEY")
DB_FILE      = os.getenv("DB_FILE")

if not DB_FILE:
    print("❌ DB_FILE not set in .env")
    sys.exit(1)
if not API_KEY:
    print("❌ API_KEY not set in .env")
    sys.exit(1)

client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL, timeout=30.0)

MODEL = "deepseek-chat"

# ============================================================
# 2. 分类体系
# ============================================================

# resource_type 枚举
VALID_TYPES = {"media", "software", "course", "book", "game", "website", "tool", "other"}

# ============================================================
# 3. 数据库
# ============================================================

def ensure_columns(cursor):
    """确保 resources 表有 category / platform 列 (不存在则 ALTER TABLE)."""
    existing = set(r[1] for r in cursor.connection.execute(
        "PRAGMA table_info(resources)"
    ).fetchall())

    for col in ["category", "platform"]:
        if col not in existing:
            print(f"   → 新增列: resources.{col}")
            cursor.execute(f"ALTER TABLE resources ADD COLUMN {col} TEXT")

    # resource_content.resource_type
    rc_cols = set(r[1] for r in cursor.connection.execute(
        "PRAGMA table_info(resource_content)"
    ).fetchall())
    if "resource_type" not in rc_cols:
        print(f"   → 新增列: resource_content.resource_type")
        cursor.execute("ALTER TABLE resource_content ADD COLUMN resource_type TEXT")

    cursor.connection.commit()


def get_unclassified(cursor, force=False, limit=None):
    """查询待分类的资源."""
    if force:
        where = "1=1"
    else:
        where = "(r.category IS NULL OR r.category = '' OR r.platform IS NULL OR r.platform = '')"

    query = f"""
        SELECT r.res_id, r.title, COALESCE(r.seo_desc, '') AS seo_desc,
               COALESCE(r.category, '') AS category,
               COALESCE(r.platform, '') AS platform
        FROM resources r
        WHERE {where}
        ORDER BY r.res_id
    """
    if limit:
        query += f" LIMIT {int(limit)}"
    return cursor.execute(query).fetchall()


def save_classification(cursor, res_id, category, platform, resource_type):
    """写入分类结果到 resources + resource_content."""
    cursor.execute("""
        UPDATE resources SET category=?, platform=? WHERE res_id=?
    """, (category, platform, res_id))

    cursor.execute("""
        INSERT INTO resource_content (resource_id, resource_type)
        VALUES (?, ?)
        ON CONFLICT(resource_id) DO UPDATE SET resource_type = excluded.resource_type
    """, (res_id, resource_type))


# ============================================================
# 4. AI 分类
# ============================================================

def build_prompt(title, seo_desc):
    """构造分类 prompt."""
    parts = [f"资源名称：{title}"]
    if seo_desc:
        parts.append(f"资源描述：{seo_desc[:300]}")
    context = "\n".join(parts)

    return f"""根据以下资源信息，判断其分类、平台和类型。

{context}

输出 JSON（三个字段）：

1. category：中文分类标签，从以下选一个最匹配的：
   纪录片 / 电影 / 剧集 / 动画 / AI工具 / 开发工具 / 设计工具 /
   效率工具 / 学习资源 / 电子书 / 游戏 / 模组 / 模板 /
   开源项目 / NAS资源 / Docker镜像 / 网站服务 / 其他

2. platform：适用平台或介质，从以下选一个最匹配的：
   Windows / Mac / Linux / Web / iOS / Android / 跨平台 / 视频 / 音频 / 电子书格式 / 其他

3. resource_type：资源类型枚举
   media（影音/纪录片/电影/剧集/动画）
   software（软件/应用/工具/插件）
   course（课程/教程/学习资料）
   book（电子书/文档/书籍）
   game（游戏/模组/MOD）
   website（网站/在线服务）
   tool（命令行工具/开发库/框架）
   other（以上都不匹配）

注意：
- 如果描述明确提到是 BBC/国家地理/Discovery 等出品的影片 → category=纪录片, resource_type=media
- 如果描述提到编程/开发/AI → 判断是工具还是课程
- 不要猜，描述不足时用"其他"

只输出 JSON：
{{"category":"纪录片","platform":"视频","resource_type":"media"}}"""


def classify(title, seo_desc=""):
    """调用 AI 分类，返回 {category, platform, resource_type} 或 None."""
    prompt = build_prompt(title, seo_desc)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)

        category = str(data.get("category", "其他")).strip()
        platform = str(data.get("platform", "其他")).strip()
        resource_type = str(data.get("resource_type", "other")).strip()

        if resource_type not in VALID_TYPES:
            resource_type = "other"

        return {
            "category": category,
            "platform": platform,
            "resource_type": resource_type,
        }
    except Exception as e:
        print(f"   ❌ {e}")
        return None


# ============================================================
# 5. --plan
# ============================================================

def cmd_plan():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    ensure_columns(cursor)

    total = cursor.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    cat_null = cursor.execute(
        "SELECT COUNT(*) FROM resources WHERE category IS NULL OR category=''"
    ).fetchone()[0]
    plat_null = cursor.execute(
        "SELECT COUNT(*) FROM resources WHERE platform IS NULL OR platform=''"
    ).fetchone()[0]
    has_both = total - max(cat_null, plat_null)

    conn.close()

    print()
    print("=" * 50)
    print("  ai_classifier — Plan")
    print("=" * 50)
    print(f"  Total resources:  {total}")
    print(f"  category NULL:    {cat_null}")
    print(f"  platform NULL:    {plat_null}")
    print(f"  already complete: {has_both}")
    print()
    if cat_null or plat_null:
        print(f"  Run: python3 ai_classifier.py --limit 10")
        print(f"       python3 ai_classifier.py")
    else:
        print(f"  ✅ All resources classified.")
    print()


# ============================================================
# 6. 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="BigPRC ai_classifier — AI resource classifier")
    parser.add_argument("--plan", action="store_true", help="Show pending counts")
    parser.add_argument("--limit", type=int, default=None, help="Max resources to classify")
    parser.add_argument("--force", action="store_true", help="Re-classify all, overwrite existing")
    args = parser.parse_args()

    if args.plan:
        cmd_plan()
        return

    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    ensure_columns(cursor)

    resources = get_unclassified(cursor, force=args.force, limit=args.limit)

    if not resources:
        print("✅ All resources already classified.")
        conn.close()
        return

    print(f"📋 Classifying {len(resources)} resources")
    print()

    ok, fail = 0, 0
    for idx, row in enumerate(resources, 1):
        res_id, title, seo_desc, old_cat, old_plat = row
        print(f"[{idx}/{len(resources)}] {res_id}  {title[:50]}")

        result = classify(title, seo_desc)
        if result:
            save_classification(cursor, res_id, result["category"],
                                result["platform"], result["resource_type"])
            conn.commit()
            ok += 1
            print(f"   ✅ {result['category']} | {result['platform']} | {result['resource_type']}")
        else:
            fail += 1

        if idx % 10 == 0:
            conn.commit()
        time.sleep(0.3)

    conn.commit()
    conn.close()

    print()
    print("=" * 50)
    print(f"  Classification: ✅ {ok}  ❌ {fail}")
    print("=" * 50)


if __name__ == "__main__":
    main()
