#!/usr/bin/env python3
"""Phase 10.10.2 — Editorial Generation Engine

Real AI-powered Editor's Take content generation with:
- A/B prompt variants (Differentiation vs Editorial Voice)
- Tier filter (spotlight/core/solid)
- Batch retry on API failure
- Guideline Check before DB write

Usage:
  python3 editorial_pilot.py --generate --tier CORE --limit 20
  python3 editorial_pilot.py --generate --prompt B --tier SOLID --limit 30
  python3 editorial_pilot.py --review
  python3 editorial_pilot.py --publish ID1 ID2 ID3
  python3 editorial_pilot.py --report
  python3 editorial_pilot.py --export /var/www/site/web/admin/data/editorial-pending.json

Rules (from PHASE10_8_1_EDITORIAL_WRITING_GUIDELINE.md):
  - No "非常优秀" "功能强大" "强烈推荐" "值得推荐"
  - No "所有人" in target_audience
  - At least 1 caveat (every resource has limits)
  - At least 1 strength
  - Editor recommendation must be 30+ chars
"""

import os, sys, json, sqlite3, re, time, logging
from datetime import datetime

from dotenv import load_dotenv
load_dotenv("/root/scripts/.env")

from db_helper import get_db
DB_FILE = get_db()
API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY = os.getenv("API_KEY")

# ── AI Client Setup ──────────────────────────────────────────
_client = None

def get_client():
    global _client
    if _client is None:
        if not API_KEY:
            print("❌ API_KEY not set in .env")
            sys.exit(1)
        from openai import OpenAI
        _client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL, timeout=90.0)
    return _client

_PRIMARY = os.getenv("AI_PRIMARY_MODEL", "deepseek-v4-pro")
_FALLBACK = os.getenv("AI_FALLBACK_MODEL", "deepseek-v4-flash")
FALLBACK_MODELS = [_PRIMARY, _FALLBACK]
ERROR_LOG = "/root/scripts/editorial_generation_errors.log"
logging.basicConfig(filename=str(ERROR_LOG), level=logging.WARNING,
                    format='%(asctime)s %(message)s')

# ── Guideline Check ──────────────────────────────────────────
FORBIDDEN_PHRASES = [
    "非常优秀", "功能强大", "强烈推荐", "值得推荐",
    "必备", "神器", "全网最全", "最好用",
]

def guideline_check(rec, audience, strengths, caveats):
    """Returns (passed: bool, issues: list[str])"""
    issues = []
    text = f"{rec} {audience}"

    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            issues.append(f"Forbidden phrase: '{phrase}'")

    if "所有人" in audience or "每个人" in audience or "用户都适合" in audience:
        issues.append("target_audience too generic (contains '所有人/每个人')")

    if len(rec.strip()) < 30:
        issues.append(f"Recommendation too short ({len(rec)} chars, need 30+)")

    if len(strengths) == 0:
        issues.append("No strengths provided")

    if len(caveats) == 0:
        issues.append("No caveats provided (every resource has limits)")

    return (len(issues) == 0, issues)


# ── Resource Type Detection ──────────────────────────────────
def detect_resource_type(category):
    """Map resource category to evaluation type for prompt routing."""
    if not category:
        return "default"
    c = category.lower()
    if any(w in c for w in ["软件","系统","工具","应用","插件","驱动"]):
        return "software"
    if any(w in c for w in ["纪录","电影","视频","影视","影片"]):
        return "documentary"
    if any(w in c for w in ["教程","课程","学习","培训","教育"]):
        return "course"
    if any(w in c for w in ["书籍","图书","文本","古籍","经典","文献","阅读"]):
        return "book"
    return "default"


# ── Type-Specific Evaluation Criteria ────────────────────────
TYPE_CRITERIA = {
    "software": """评估角度（软件/工具）：
- 版本价值：是否官方原版？是否已从官方下架？是否为买断版（非订阅）？
- 平台兼容：支持哪些系统？是否有32/64位区分？
- 使用场景：适合什么工作流？解决了什么具体问题？
- 替代关系：和同类软件比有什么不可替代的地方？""",

    "documentary": """评估角度（纪录片/视频）：
- 版本优势：是否为原盘压制？和流媒体版有什么区别？
- 内容稀缺：是否在流媒体平台已下架或需要付费？
- 完整性：是否包含特辑/花絮/多语言字幕？
- 长期价值：是否具有重复观看或教学使用的长期价值？""",

    "course": """评估角度（教程/课程）：
- 知识体系：是否覆盖完整学习路径？还是碎片化内容？
- 学习阶段：适合什么水平的学习者？是否有前置要求？
- 版本匹配：教程对应的软件版本是否仍然可用？
- 语言质量：字幕/讲解是机翻还是人工？是否准确？""",

    "book": """评估角度（书籍/文本）：
- 版本权威：是否为学界公认的标准版本？注释者/译者是否有学术地位？
- 内容体系：是否包含注释/翻译/原文对照？排版是否适合阅读？
- 版本价值：和市面上其他版本相比有什么优势？
- 长期价值：是否具有反复查阅的参考价值？""",

    "default": """评估角度：
- 版本稀缺：这个版本为什么值得保存？
- 可用性：下载后能否直接使用？是否需要额外配置？
- 长期价值：这个资源在5年后还有用吗？""",
}

STRENGTH_EXAMPLES = {
    "software": """反面示例（禁止）：+ 功能强大 + 非常好用 + 界面美观 + 值得推荐
正面示例：+ 官方原版ISO，SHA256可验证，无任何修改
+ 包含Access和Publisher（Microsoft 365默认不含这些组件）
+ 支持32位和64位双版本，兼容新旧设备""",

    "documentary": """反面示例（禁止）：+ 画质清晰 + 内容丰富 + 非常精彩 + 必看神作
正面示例：+ 4K HDR原盘压制，非流媒体录制版，保留了暗部细节
+ 中英双语字幕可切换，适合英语学习场景
+ 两季完整收录，不需要分开寻找不同版本""",

    "course": """反面示例（禁止）：+ 讲解详细 + 非常实用 + 适合学习 + 内容全面
正面示例：+ 覆盖建模→渲染完整流程，不需要另外找教程
+ 每个案例都有源文件，可以跟着操作练习
+ 中文字幕为人工翻译，非机翻，专业术语准确""",

    "book": """反面示例（禁止）：+ 内容经典 + 值得阅读 + 排版精美 + 非常推荐
正面示例：+ 四层对照排版（原文/郭注/成疏/今译），不需要来回翻书
+ 郭象注是学界公认标准注本，引用可靠
+ 现代汉语翻译保持了原文简洁，没有过度白话化""",

    "default": """反面示例（禁止）：+ 非常实用 + 质量很高 + 值得收藏 + 强烈推荐
正面示例：+ 官方原版，未经第三方修改
+ 包含全部组件，不需要额外下载
+ 支持离线使用，不需要网络连接""",
}


# ── Editorial Prompt V3 ──────────────────────────────────────
PROMPT_V3 = """你是 BigPRC 的数字资源策展编辑。

BigPRC 定位：帮助用户找到值得长期收藏的数字资源。
用户不是来看评测的，而是判断：是否值得下载保存？和网上其他版本有什么不同？

═══════════════════════════════════════
资源信息（仅基于以下事实，不要推测）：
═══════════════════════════════════════
名称: {title}
类型: {category}
资源形态: {resource_type}
大小: {file_size}
平台: {platform}
版本: {version}
所属专题: {collections}
现有说明: {seo_desc}

═══════════════════════════════════════
评估标准（{resource_type}类资源）：
═══════════════════════════════════════
{type_criteria}

═══════════════════════════════════════
写作规则：
═══════════════════════════════════════

【反幻觉】只使用以上信息。不知道就不要写。信息不足以做出有意义判断时，
返回 skip:true。不要用泛泛的夸奖填充空白。

【禁止词】禁止：震撼 惊艳 必看 神作 强烈推荐 非常优秀 功能强大
最好用 必备 神器 全网最全 不容错过 巨好用 值得收藏 不可错过
经典之作 精心整理 强烈建议 必下 绝佳 完美

【禁止第一人称】禁止："我认为""我推荐""我看过""我觉得"
使用客观编辑视角。

【编辑声音】BigPRC编辑的推荐读起来像这样：
"这个版本是官方原版，没有第三方修改。网上流传的大多数版本
都捆绑了额外软件，这个是干净的起点。"
而不是："这款软件功能强大，界面友好，非常优秀，强烈推荐。"

【skip规则】如果资源无明显差异化特征，或信息不足以做出编辑判断，返回：
{{"skip":true,"skip_reason":"简短的跳过原因"}}

═══════════════════════════════════════
字段要求：
═══════════════════════════════════════

editorial_score (0-100): 综合评分。依据：稀缺性(25) + 长期价值(25) +
  用户价值(25) + 信息完整度(25)。60以上才值得写推荐。

editor_recommendation (1-3句): 为什么这个具体版本值得保留在硬盘里？
  不要描述内容（seo_desc已做），要给出选择判断。

target_audience (1句或空): 从以下选一种并具体化：
  零基础入门/有基础进阶/专业从业者/学生/内容创作者/开发者/家庭用户/教育者
  信息不足时写空字符串。

strengths (2-3条，+ 号开头):
{strength_examples}

caveats (1-3条，· 号开头): 用户下载前必须知道的信息。
  技术限制/范围限制/质量差距/使用门槛。不是"画质一般""文件较大"。

输出严格JSON（不含markdown代码块）：
{{"editorial_score":0-100,"editor_recommendation":"...","target_audience":"...","strengths":["+ ..."],"caveats":["· ..."]}}
或 {{"skip":true,"skip_reason":"..."}}"""

# Backward-compatible aliases
PROMPT_A = PROMPT_V3
PROMPT_B = PROMPT_V3


# ── AI Generation ────────────────────────────────────────────
def call_ai(prompt):
    """Call AI API with fallback chain. Returns (parsed_dict, model_name) or (None, None)."""
    client = get_client()

    for model in FALLBACK_MODELS:
        # Attempt 1: JSON mode
        try:
            print(f"   [{model}] ", end="", flush=True)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1200,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content.strip()
            parsed = json.loads(raw)
            print("✅")
            return parsed, model
        except (json.JSONDecodeError, TypeError):
            print("retry...", end=" ", flush=True)
            try:
                resp2 = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1200,
                )
                raw2 = resp2.choices[0].message.content.strip()
                parsed2 = json.loads(raw2)
                print("✅")
                return parsed2, model
            except Exception:
                pass
        except Exception as e:
            print(f"err ({e})", end=" ", flush=True)
            continue

    print("❌ all models failed")
    return None, None


def generate_editorial(resource, prompt_variant="A"):
    """Generate Editor's Take content using AI (V3 with type routing).
    Returns dict with editorial fields + score, or None on failure/skip.
    Returns special sentinel {{"skip": True, "reason": "..."}} for skipped resources."""
    rtype = detect_resource_type(resource.get("category", ""))
    criteria = TYPE_CRITERIA.get(rtype, TYPE_CRITERIA["default"])
    examples = STRENGTH_EXAMPLES.get(rtype, STRENGTH_EXAMPLES["default"])

    prompt = PROMPT_V3.format(
        title=resource.get("title", ""),
        category=resource.get("category", ""),
        resource_type=rtype,
        type_criteria=criteria,
        strength_examples=examples,
        file_size=resource.get("file_size", "") or resource.get("size", ""),
        platform=resource.get("platform", ""),
        version=resource.get("version", ""),
        collections=resource.get("collections", "") or resource.get("coll_titles", ""),
        seo_desc=(resource.get("seo_desc", "") or "")[:300],
    )
    result, model_used = call_ai(prompt)
    if not result:
        return None

    # Handle skip signal
    if result.get("skip"):
        return {"skip": True, "reason": result.get("skip_reason", result.get("reason", "未说明"))}

    # Normalize output
    score = result.get("editorial_score", 0)
    if isinstance(score, str):
        try:
            score = int(score)
        except ValueError:
            score = 0

    return {
        "editor_recommendation": str(result.get("editor_recommendation", "")),
        "target_audience": str(result.get("target_audience", "")),
        "strengths": result.get("strengths", []) if isinstance(result.get("strengths"), list) else [],
        "caveats": result.get("caveats", []) if isinstance(result.get("caveats"), list) else [],
        "editorial_score": min(max(score, 0), 100),
        "ai_model": model_used,
        "resource_type": rtype,
    }


# ── Database Operations ──────────────────────────────────────
def get_pilot_resources(conn, limit=50, tier=None, force=False):
    """Select resources for editorial generation.
    tier: 'spotlight', 'core', 'solid' (None = all)
    force: if True, include rejected resources for regeneration."""
    cur = conn.cursor()
    where = "WHERE (r.editorial_status IS NULL"
    if force:
        where += " OR r.editorial_status = 'rejected'"
    where += ")"

    if tier == 'spotlight':
        where += " AND rc.spotlight = 1"
    elif tier in ('core', 'solid'):
        # core/solid: resources assigned to at least one collection
        # (quality tier mapping TBD — no c.quality column in current schema)
        where += " AND rc.collection_id IS NOT NULL"

    query = f"""
        SELECT r.res_id, r.title, r.category, r.file_size, r.platform,
               r.version, r.seo_desc,
               GROUP_CONCAT(c.title, ', ') as coll_titles
        FROM resources r
        LEFT JOIN resource_collections rc ON r.res_id = rc.resource_id
        LEFT JOIN collections c ON rc.collection_id = c.id
        {where}
        GROUP BY r.res_id
        ORDER BY
            CASE WHEN rc.spotlight = 1 THEN 0 ELSE 1 END,
            RANDOM()
        LIMIT ?
    """
    cur.execute(query, (limit,))
    return cur.fetchall()


def insert_editorial(conn, res_id, data, dry_run=False):
    """Write editorial content to database. Only if editorial_status IS NULL."""
    cur = conn.cursor()
    cur.execute("SELECT editorial_status FROM resources WHERE res_id=?", (res_id,))
    row = cur.fetchone()
    if row and row[0] is not None:
        return False, "Already has editorial content"

    if dry_run:
        return True, "DRY-RUN: would write"

    cur.execute("""
        UPDATE resources SET
            editor_recommendation = ?,
            target_audience = ?,
            strengths = ?,
            caveats = ?,
            editorial_status = 'draft',
            generated_at = ?,
            ai_model = ?
        WHERE res_id = ?
    """, (
        data["editor_recommendation"],
        data["target_audience"],
        json.dumps(data["strengths"], ensure_ascii=False),
        json.dumps(data["caveats"], ensure_ascii=False),
        datetime.now().isoformat(),
        data.get("ai_model", "unknown"),
        res_id,
    ))
    conn.commit()
    return True, "Written (draft)"


def publish_editorial(conn, res_id):
    """Set status to published (after human review)."""
    cur = conn.cursor()
    cur.execute("SELECT editorial_status FROM resources WHERE res_id=?", (res_id,))
    row = cur.fetchone()
    if not row or row[0] is None:
        return False, "No editorial content to publish"
    if row[0] == 'published':
        return False, "Already published"

    cur.execute("""
        UPDATE resources SET
            editorial_status = 'published',
            reviewed_at = ?
        WHERE res_id = ?
    """, (datetime.now().isoformat(), res_id))
    conn.commit()
    return True, "Published"


def pilot_report(conn):
    """Generate pilot statistics."""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN editorial_status = 'draft' THEN 1 ELSE 0 END) as drafts,
            SUM(CASE WHEN editorial_status = 'reviewed' THEN 1 ELSE 0 END) as reviewed,
            SUM(CASE WHEN editorial_status = 'published' THEN 1 ELSE 0 END) as published,
            AVG(LENGTH(editor_recommendation)) as avg_rec_len,
            AVG(LENGTH(target_audience)) as avg_aud_len
        FROM resources
        WHERE editorial_status IS NOT NULL
    """)
    row = cur.fetchone()
    print(f"\n=== Editorial Pilot Report ===")
    print(f"Total with editorial:  {row[0] or 0}")
    print(f"  Draft:              {row[1] or 0}")
    print(f"  Reviewed:           {row[2] or 0}")
    print(f"  Published:          {row[3] or 0}")
    print(f"  Avg rec length:     {row[4] or 0:.0f} chars")
    print(f"  Avg audience length: {row[5] or 0:.0f} chars")
    print()

    # Strengths/caveats counts
    cur.execute("SELECT strengths, caveats FROM resources WHERE editorial_status IS NOT NULL")
    s_counts, c_counts = [], []
    for s, c in cur.fetchall():
        try:
            s_counts.append(len(json.loads(s)) if s else 0)
            c_counts.append(len(json.loads(c)) if c else 0)
        except json.JSONDecodeError:
            pass
    if s_counts:
        print(f"  Avg strengths: {sum(s_counts)/len(s_counts):.1f}")
        print(f"  Avg caveats:   {sum(c_counts)/len(c_counts):.1f}")


# ── Production Metrics ───────────────────────────────────────
def production_metrics(conn):
    """Print production dashboard for editorial pipeline."""
    cur = conn.cursor()

    # Generation stats
    cur.execute("""
        SELECT
            COUNT(*) as total_gen,
            SUM(CASE WHEN editorial_status = 'draft' THEN 1 ELSE 0 END) as drafts,
            SUM(CASE WHEN editorial_status = 'reviewed' THEN 1 ELSE 0 END) as reviewed,
            SUM(CASE WHEN editorial_status = 'published' THEN 1 ELSE 0 END) as published,
            SUM(CASE WHEN editorial_status = 'rejected' THEN 1 ELSE 0 END) as rejected,
            AVG(LENGTH(editor_recommendation)) as avg_rec_len,
            AVG(LENGTH(target_audience)) as avg_aud_len
        FROM resources
        WHERE editorial_status IS NOT NULL
    """)
    r = cur.fetchone()

    # Model usage
    cur.execute("""
        SELECT ai_model, COUNT(*) as cnt
        FROM resources
        WHERE ai_model IS NOT NULL
        GROUP BY ai_model ORDER BY cnt DESC
    """)
    models = cur.fetchall()

    # Strengths/caveats averages
    cur.execute("SELECT strengths, caveats FROM resources WHERE editorial_status IS NOT NULL")
    s_lens, c_lens = [], []
    for s, c in cur.fetchall():
        try:
            s_lens.append(len(json.loads(s)) if s else 0)
            c_lens.append(len(json.loads(c)) if c else 0)
        except json.JSONDecodeError:
            pass

    print("\n=== Editorial Production Metrics ===")
    print(f"Total generated:     {r['total_gen'] or 0}")
    print(f"  Draft:             {r['drafts'] or 0}")
    print(f"  Reviewed:          {r['reviewed'] or 0}")
    print(f"  Published:         {r['published'] or 0}")
    print(f"  Rejected:          {r['rejected'] or 0}")
    if r['total_gen']:
        reject_rate = (r['rejected'] or 0) / r['total_gen'] * 100
        publish_rate = (r['published'] or 0) / r['total_gen'] * 100
        print(f"  Publish rate:      {publish_rate:.0f}%")
        print(f"  Reject rate:       {reject_rate:.0f}%")
    print(f"Avg rec length:      {r['avg_rec_len'] or 0:.0f} chars")
    print(f"Avg audience length: {r['avg_aud_len'] or 0:.0f} chars")
    if s_lens:
        print(f"Avg strengths:       {sum(s_lens)/len(s_lens):.1f}")
        print(f"Avg caveats:         {sum(c_lens)/len(c_lens):.1f}")
    if models:
        print(f"Model usage:")
        for m, c in models:
            print(f"  {m}: {c}")
    print()

    # Generation times
    cur.execute("""
        SELECT generated_at, reviewed_at
        FROM resources
        WHERE generated_at IS NOT NULL AND reviewed_at IS NOT NULL
        LIMIT 20
    """)
    # Simple pass/fail thresholds
    checks = []
    if (r['published'] or 0) / max(r['total_gen'] or 1, 1) < 0.5:
        checks.append("⚠ Publish rate < 50%")
    if (r['rejected'] or 0) / max(r['total_gen'] or 1, 1) > 0.1:
        checks.append("⚠ Reject rate > 10%")
    if (r['avg_rec_len'] or 0) < 40:
        checks.append("⚠ Avg recommendation < 40 chars (too short)")
    if s_lens and sum(s_lens)/len(s_lens) < 2.0:
        checks.append("⚠ Avg strengths < 2.0")
    if c_lens and sum(c_lens)/len(c_lens) < 1.0:
        checks.append("⚠ Avg caveats < 1.0")

    if checks:
        print("Quality Alerts:")
        for c in checks:
            print(f"  {c}")
    else:
        print("✅ All quality thresholds met.")

    return {
        "total": r['total_gen'] or 0,
        "published": r['published'] or 0,
        "rejected": r['rejected'] or 0,
        "publish_rate": (r['published'] or 0) / max(r['total_gen'] or 1, 1),
        "reject_rate": (r['rejected'] or 0) / max(r['total_gen'] or 1, 1),
        "avg_rec_len": r['avg_rec_len'] or 0,
        "avg_strengths": sum(s_lens)/len(s_lens) if s_lens else 0,
        "avg_caveats": sum(c_lens)/len(c_lens) if c_lens else 0,
    }


# ── Export for Admin UI ──────────────────────────────────────
def export_review_data(conn, out_path):
    """Export pending/reviewed editorial data for admin UI consumption."""
    cur = conn.cursor()
    cur.execute("""
        SELECT r.res_id, r.title, r.category,
               r.editor_recommendation, r.target_audience,
               r.strengths, r.caveats,
               r.editorial_status, r.generated_at, r.reviewed_at,
               r.ai_model,
               GROUP_CONCAT(c.title, ', ') as collections
        FROM resources r
        LEFT JOIN resource_collections rc ON r.res_id = rc.resource_id
        LEFT JOIN collections c ON rc.collection_id = c.id
        WHERE r.editorial_status IN ('draft', 'reviewed')
        GROUP BY r.res_id
        ORDER BY
            CASE r.editorial_status WHEN 'draft' THEN 0 ELSE 1 END,
            r.generated_at DESC
    """)
    rows = []
    for r in cur.fetchall():
        row = dict(r)
        # Parse JSON arrays
        for field in ['strengths', 'caveats']:
            try:
                row[field] = json.loads(row[field]) if row[field] else []
            except json.JSONDecodeError:
                row[field] = []
        rows.append(row)

    data = {
        "generated_at": datetime.now().isoformat(),
        "total": len(rows),
        "drafts": sum(1 for r in rows if r['editorial_status'] == 'draft'),
        "reviewed": sum(1 for r in rows if r['editorial_status'] == 'reviewed'),
        "items": rows,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Exported {len(rows)} items → {out_path}")


# ── CLI ──────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Editorial Content Pilot")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--generate", action="store_true", help="Generate and write drafts")
    parser.add_argument("--tier", type=str, choices=["spotlight","core","solid"], help="Filter by quality tier")
    parser.add_argument("--limit", type=int, default=50, help="Max resources to generate (default 50)")
    parser.add_argument("--prompt", type=str, choices=["A","B"], default="A", help="Prompt variant: A=Differentiation, B=Editorial Voice")
    parser.add_argument("--force", action="store_true", help="Regenerate rejected resources")
    parser.add_argument("--review", action="store_true", help="List drafts awaiting review")
    parser.add_argument("--publish", nargs="+", metavar="ID", help="Publish one or more resources")
    parser.add_argument("--report", action="store_true", help="Print pilot statistics")
    parser.add_argument("--metrics", action="store_true", help="Print production metrics dashboard")
    parser.add_argument("--export", type=str, metavar="PATH", help="Export pending data as JSON for admin UI")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    if args.review:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, title, editor_recommendation, target_audience
            FROM resources
            WHERE editorial_status = 'draft'
            ORDER BY generated_at
        """)
        for r in cur.fetchall():
            print(f"\n── {r['res_id']} ──")
            print(f"Title: {r['title']}")
            print(f"Rec:   {r['editor_recommendation'][:100]}...")
            print(f"Aud:   {r['target_audience']}")
        return

    if args.publish:
        for rid in args.publish:
            ok, msg = publish_editorial(conn, rid)
            print(f"{'✅' if ok else '❌'} {rid}: {msg}")
        return

    if args.report:
        pilot_report(conn)
        return

    if args.metrics:
        production_metrics(conn)
        return

    if args.export:
        export_review_data(conn, args.export)
        return

    if args.generate:
        resources = get_pilot_resources(conn, limit=args.limit, tier=args.tier, force=args.force)
        print(f"Selected {len(resources)} resources (tier={args.tier or 'all'}, prompt={args.prompt}, limit={args.limit})")
        if args.dry_run:
            for i, r in enumerate(resources[:10]):
                print(f"  {i+1}. [{r['res_id']}] {r['title'][:60]}")
            if len(resources) > 10:
                print(f"  ... and {len(resources)-10} more")
            return

        ok, fail, skipped, skip_no_write = 0, 0, 0, 0
        for i, r in enumerate(resources):
            rid = r['res_id']
            title = r['title'][:50]
            rtype = detect_resource_type(r.get('category', ''))
            print(f"[{i+1}/{len(resources)}] {rid} [{rtype}] {title}")

            # Generate with retry
            data = None
            for attempt in range(3):
                data = generate_editorial(dict(r), prompt_variant=args.prompt)
                if data:
                    break
                print(f"   Retry {attempt+1}/3...")
                time.sleep(2)

            if not data:
                print(f"   ❌ Failed after 3 attempts")
                logging.warning(f"AI_FAIL {rid} {title}")
                fail += 1
                continue

            # Handle AI skip signal
            if data.get("skip"):
                reason = data.get("reason", "未说明")
                print(f"   ⏩ SKIPPED: {reason}")
                logging.info(f"SKIP {rid} [{rtype}]: {reason}")
                skipped += 1
                continue

            # Log editorial score
            score = data.get("editorial_score", 0)
            print(f"   📊 Score: {score}/100", end="")

            # Guideline Check
            passed, issues = guideline_check(
                data["editor_recommendation"],
                data["target_audience"],
                data["strengths"],
                data["caveats"],
            )
            if not passed:
                print(f"  ⚠ Guideline: {', '.join(issues)}")
                logging.warning(f"GUIDELINE_FAIL {rid}: {'; '.join(issues)}")
            else:
                print()

            # Write to DB
            wrote, msg = insert_editorial(conn, rid, data, dry_run=args.dry_run)
            if wrote:
                ok += 1
                print(f"   ✅ {msg}")
            else:
                skip_no_write += 1
                print(f"   ⏭ {msg}")

        print(f"\nDone: ✅ {ok} generated  ⏩ {skipped} AI-skipped  ⏭ {skip_no_write} already-exist  ❌ {fail} failed")
        if fail > 0:
            print(f"Errors logged to: {ERROR_LOG}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
