#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC ai_seo_writer.py v2.0 — AI content generator for resource_content table.

Upgrade (v1 → v2):
  - Data source: SQLite (resources LEFT JOIN resource_content) instead of Excel
  - Output:      resource_content (tagline, ai_summary, ai_keywords, ai_reason_candidates)
  - Strategy:    Round 1 = one JSON call → 3 fields. Round 2 = one call → reason candidates.
  - Protection:  editor_status='approved' → NEVER touch. Existing value → skip (unless --force).
  - SQL safety:  COALESCE(editor_status,'pending') — avoids NULL != 'approved' trap.

Usage:
  python3 ai_seo_writer.py --plan           # Show pending counts per field
  python3 ai_seo_writer.py --limit 10       # Test 10 resources (both rounds)
  python3 ai_seo_writer.py --round 1        # Only Round 1 (tagline + summary + keywords)
  python3 ai_seo_writer.py --round 2        # Only Round 2 (reason candidates)
  python3 ai_seo_writer.py                  # Full run, all pending
  python3 ai_seo_writer.py --force          # Overwrite existing AI content
  python3 ai_seo_writer.py --resume         # Same as default (skip filled fields)

Config: reads DB_FILE / API_BASE_URL / API_KEY from /root/scripts/.env
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
# 1. 配置加载
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY      = os.getenv("API_KEY")
DB_FILE      = os.getenv("DB_FILE")

if not DB_FILE:
    print("❌ DB_FILE not set in .env")
    print("   Add: DB_FILE=/root/scripts/database.db")
    sys.exit(1)

if not API_KEY:
    print("❌ API_KEY not set in .env")
    sys.exit(1)

client = OpenAI(
    api_key=API_KEY,
    base_url=API_BASE_URL,
    timeout=60.0
)

FALLBACK_MODELS = [
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "deepseek-v4-pro[1]"
]

# ============================================================
# 2. 内容保护工具
# ============================================================

def has_value(value):
    """有意义的值 (排除 None / 空字符串 / 纯空格)."""
    return bool(value and str(value).strip())


def should_generate_field(cursor, resource_id, field_name, force=False):
    """判断某个字段是否需要 AI 生成.

    优先级链:
      1. 人工审核过 (editor_status='approved') → 绝不覆盖
      2. 已有 AI 值 → 跳过 (除非 --force)
      3. 字段为空/不存在 → 生成
    """
    if force:
        return True

    cursor.execute("""
        SELECT {field}, COALESCE(editor_status, 'pending')
        FROM resource_content
        WHERE resource_id = ?
    """.format(field=field_name), (resource_id,))
    row = cursor.fetchone()

    if row is None:
        return True          # resource_content 里还没有这条记录

    existing_value, status = row

    if status == 'approved':
        return False         # 人工审核过，绝不碰

    if has_value(existing_value):
        return False         # 已有 AI 生成内容

    return True


# ============================================================
# 3. 文本校验
# ============================================================

FORBIDDEN_WORDS = [
    "世界领先", "最强", "最好", "第一", "无与伦比",
    "革命性", "颠覆性", "史无前例", "前所未有",
    "作为一个人工智能", "抱歉", "无法提供", "我不能", "违反政策",
]

FORBIDDEN_BRANDS = [
    "夸克", "百度网盘", "阿里云盘", "迅雷", "天翼云盘",
    "115网盘", "移动云盘", "城通网盘",
]


def validate_text(text, field_name, max_len=None):
    """校验单段文本: 非空 / 自动截断超长 / 禁用词 / 违禁品牌."""
    if not text or not str(text).strip():
        raise ValueError(f"[{field_name}] 返回内容为空")

    text = str(text).strip()

    if max_len and len(text) > max_len:
        print(f"   ⚡ {field_name} 自动截断 ({len(text)} → {max_len})")
        text = text[:max_len]

    for word in FORBIDDEN_WORDS:
        if word in text:
            raise ValueError(f"[{field_name}] 包含禁用词: {word}")

    for brand in FORBIDDEN_BRANDS:
        if brand in text:
            raise ValueError(f"[{field_name}] 包含违禁品牌词: {brand}")

    return text


def validate_round1_output(data):
    """校验 Round 1 JSON 输出 → 清洗后 dict.

    Returns: {"tagline", "ai_summary", "ai_keywords", "confidence"} or raises ValueError.
    """
    if not isinstance(data, dict):
        raise ValueError("Round 1 输出必须是 JSON 对象")

    tagline     = data.get("tagline", "")
    ai_summary  = data.get("ai_summary", "")
    ai_keywords = data.get("ai_keywords", [])
    confidence  = data.get("confidence", 0.5)

    validate_text(tagline, "tagline", max_len=25)
    validate_text(ai_summary, "ai_summary", max_len=120)

    if not isinstance(ai_keywords, list):
        raise ValueError("ai_keywords 必须是数组")
    if len(ai_keywords) < 3:
        raise ValueError(f"ai_keywords 数量不足 ({len(ai_keywords)} < 3)")
    if len(ai_keywords) > 10:
        ai_keywords = ai_keywords[:10]

    cleaned_kw = []
    for kw in ai_keywords:
        if not isinstance(kw, str) or not kw.strip():
            raise ValueError("ai_keywords 包含空值")
        cleaned_kw.append(str(kw).strip())

    # Normalize confidence
    try:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.5

    return {
        "tagline":     tagline.strip(),
        "ai_summary":  ai_summary.strip(),
        "ai_keywords": json.dumps(cleaned_kw, ensure_ascii=False),
        "confidence":  confidence,
    }


def validate_round2_output(data):
    """校验 Round 2 JSON 输出 → JSON 字符串.

    Returns: JSON string of reason candidates array
    Raises:  ValueError on failure
    """
    candidates = None

    if isinstance(data, dict):
        candidates = data.get("ai_reason_candidates", [])
    elif isinstance(data, list):
        candidates = data

    if not isinstance(candidates, list):
        raise ValueError("ai_reason_candidates 必须是数组")

    if len(candidates) < 2:
        raise ValueError(f"ai_reason_candidates 数量不足 ({len(candidates)} < 2)")
    if len(candidates) > 6:
        candidates = candidates[:6]

    cleaned = []
    for item in candidates:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("ai_reason_candidates 包含空值")
        text = str(item).strip()
        validate_text(text, "reason_candidate", max_len=100)
        cleaned.append(text)

    return json.dumps(cleaned, ensure_ascii=False)


# ============================================================
# 4. AI 生成 — Prompt 构建 + 模型调用
# ============================================================

def build_round1_prompt(title, category, platform, version, seo_desc="", resource_type=""):
    """Round 1: category-aware + resource_type tagline/summary/keywords/confidence."""
    context_parts = [f"Title: {title}"]
    if category:       context_parts.append(f"Category: {category}")
    if resource_type:  context_parts.append(f"Type: {resource_type}")
    if platform:       context_parts.append(f"Platform: {platform}")
    if version:        context_parts.append(f"Version: {version}")
    if seo_desc:       context_parts.append(f"Description: {seo_desc[:250]}")
    context = "\n".join(context_parts)

    DOC_CATS = {"NaturalScience","HistoryCulture","TravelGeography","ArtDesign","FoodLifestyle","ChineseCulture"}
    SW_CATS  = {"SoftwareTool","DevProgramming","AITech","DesignCreative"}
    COURSE_CATS = {"StudyCourse","BusinessCareer"}
    BOOK_CATS   = {"EbookRead"}
    GAME_CATS   = {"GamePlay"}
    KIDS_CATS   = {"KidsEducation"}

    cat_set = {category} if category else set()
    if cat_set & DOC_CATS:
        rule = """Documentary/video resource. Tagline: theme + why it matters.
  Good: "Uncover the survival code of big cats" "Africa's magnificent ecological tapestry"
  Bad: "Nature documentary" "BBC documentary series"
  NEVER end with "documentary" "video" "film" -- those are labels, not positioning."""
    elif cat_set & SW_CATS:
        rule = """Software/tool resource. Tagline: problem solved + value gained.
  Good: "AI-powered coding, faster development" "Cross-platform knowledge management"
  Bad: "AI tool" "Programming software"
  NEVER end with "software" "tool" "app" "platform"."""
    elif cat_set & COURSE_CATS:
        rule = """Course/learning resource. Tagline: learning goal + who it's for.
  Good: "Master Python data analysis from scratch" "Systematic ML fundamentals"
  Bad: "Programming course" "Python tutorial"
  NEVER end with "course" "tutorial" "textbook"."""
    elif cat_set & BOOK_CATS:
        rule = """Ebook/document resource. Tagline: core content + reader benefit.
  Good: "Comprehensive dictionary collection for scholars"
  Bad: "Book collection" "PDF bundle"
  NEVER end with "book" "ebook" "PDF"."""
    elif cat_set & GAME_CATS:
        rule = """Game/mod resource. Tagline: core experience + unique feature.
  Good: "Immersive open-world role-playing" "Strategic card drafting"
  Bad: "Action game" "Strategy game"
  NEVER end with "game" "mod"."""
    elif cat_set & KIDS_CATS:
        rule = """Kids education resource. Tagline: what kids learn + how.
  Good: "Fun English phonics for ages 3-6" "Animated science for preschoolers"
  Bad: "Kids video" "Children education"
  NEVER end with "video" "animation" "course"."""
    else:
        rule = """General resource. Tagline: unique value, not a category label.
  Good: "Explore how Earth's life system works" "Boost coding efficiency with AI"
  Bad: "Resource collection" "Tool set"
  NEVER end with a generic category word."""

    return f"""{rule}

{context}

Output JSON with four fields:

1. tagline (in Chinese, max 20 chars): editorial positioning. Combine "what" + "why".
   MUST be Chinese (中文). NEVER end with category words like "纪录片" "软件" "工具".
2. ai_summary (max 50 chars): what problem, who is it for. No templates.
3. ai_keywords (5-8 precise terms): searchable, specific. Never "software" "tool" "resource".
4. confidence (0-1): tagline accuracy. Rich description -> >0.9. Title only -> <0.7.

No marketing buzzwords. No "As an AI" apologies. Every resource unique.

JSON only:
{{"tagline":"...","ai_summary":"...","ai_keywords":["...","..."],"confidence":0.9}}"""


def build_round2_prompt(title, category, platform, summary, seo_desc="", resource_type=""):
    """Round 2: 生成 ai_reason_candidates (推荐理由候选)."""
    context_parts = [f"资源名称：{title}"]
    if category: context_parts.append(f"分类：{category}")
    if platform: context_parts.append(f"平台：{platform}")
    if summary:  context_parts.append(f"简介：{summary}")
    if seo_desc:       context_parts.append(f"详细描述：{seo_desc[:200]}")
    if resource_type:  context_parts.append(f"Type: {resource_type}")
    context = "\n".join(context_parts)

    return f"""为以下资源生成推荐理由候选。

{context}

要求：
1. 输出严格 JSON 格式：{{"ai_reason_candidates":["理由1","理由2","理由3"]}}
2. 生成 3-5 条推荐理由
3. 每条理由 50 字以内
4. 理由必须具体、事实性，避免空洞营销语言

正确示例：
- "相比传统IDE，它把AI能力直接融入编码流程，减少切换成本"
- "适合希望提升效率但不想学习复杂AI工具的开发者"
- "开源免费，社区活跃，适合作为长期使用的开发环境"

错误示例（禁止）：
- "这是世界领先的软件"（营销腔）
- "非常强大，非常好用"（空洞无物）
- "推荐大家使用"（无信息量）

禁止：使用"强大的""顶级的""最好的""世界领先"等营销词。
每条资源的理由必须有差异，禁止套模板。

只输出 JSON，不要任何其他文字。"""


def call_ai_with_fallback(prompt, is_json=True):
    """调用 AI API，带模型降级链。JSON 模式失败时回退到普通文本再解析.

    Returns: parsed dict/list (is_json=True) or str (is_json=False), None on total failure.
    """
    for model_name in FALLBACK_MODELS:
        # ---- 尝试 1: JSON mode ----
        try:
            print(f"   ⏳ [{model_name}] JSON mode ...", end=" ", flush=True)

            kwargs = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1500,
                "response_format": {"type": "json_object"},
            }
            response = client.chat.completions.create(**kwargs)
            raw = response.choices[0].message.content.strip()

            parsed = json.loads(raw)
            print("✅")
            return parsed

        except (json.JSONDecodeError, TypeError) as e:
            # JSON mode returned non-JSON — try parsing anyway
            print(f"parse err, retrying...", end=" ", flush=True)
            try:
                fallback_kwargs = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 1500,
                }
                # Don't use response_format for fallback
                response2 = client.chat.completions.create(**fallback_kwargs)
                raw2 = response2.choices[0].message.content.strip()
                parsed2 = json.loads(raw2)
                print("✅")
                return parsed2
            except Exception:
                pass  # fall through to next model

        except Exception as e:
            # ---- 尝试 2: 同模型不用 JSON mode ----
            print(f"err, retry without JSON mode ...", end=" ", flush=True)
            try:
                kwargs2 = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 1500,
                }
                response2 = client.chat.completions.create(**kwargs2)
                raw2 = response2.choices[0].message.content.strip()

                if is_json:
                    parsed = json.loads(raw2)
                    print("✅")
                    return parsed
                else:
                    print("✅")
                    return raw2
            except (json.JSONDecodeError, TypeError):
                print(f"JSON parse failed")
                continue
            except Exception as e2:
                print(f"❌ ({e2})")
                continue

    print("   🚨 所有模型均失败")
    return None


def generate_round1(title, category="", platform="", version="", seo_desc="", resource_type=""):
    """Round 1: 一次 API 调用生成 tagline + ai_summary + ai_keywords + confidence.

    Returns: {"tagline", "ai_summary", "ai_keywords", "confidence"} or None
    """
    prompt = build_round1_prompt(title, category, platform, version, seo_desc, resource_type)
    data = call_ai_with_fallback(prompt, is_json=True)

    if data is None:
        return None

    try:
        return validate_round1_output(data)
    except ValueError as e:
        print(f"   ⚠️ 校验失败: {e}")
        return None


def generate_round2(title, category="", platform="", summary="", seo_desc="", resource_type=""):
    """Round 2: 生成 ai_reason_candidates.

    Returns: JSON string of reason candidates array, or None
    """
    prompt = build_round2_prompt(title, category, platform, summary, seo_desc, resource_type)
    data = call_ai_with_fallback(prompt, is_json=True)

    if data is None:
        return None

    try:
        return validate_round2_output(data)
    except ValueError as e:
        print(f"   ⚠️ 校验失败: {e}")
        return None


# ============================================================
# 5. 数据库读写
# ============================================================

def get_pending_resources(cursor, round_num, force=False, limit=None):
    """查询需要 AI 生成内容的资源列表.

    使用 COALESCE 避免 NULL != 'approved' 陷阱。
    """
    if round_num == 1:
        if force:
            where = "1=1"
        else:
            where = """COALESCE(rc.editor_status, 'pending') != 'approved'
              AND (rc.resource_id IS NULL
                   OR rc.tagline IS NULL OR rc.tagline = ''
                   OR rc.ai_summary IS NULL OR rc.ai_summary = ''
                   OR rc.ai_keywords IS NULL OR rc.ai_keywords = '')"""
    elif round_num == 2:
        if force:
            where = "1=1"
        else:
            where = """COALESCE(rc.editor_status, 'pending') != 'approved'
              AND (rc.resource_id IS NULL
                   OR rc.ai_reason_candidates IS NULL OR rc.ai_reason_candidates = '')"""
    else:
        # Both rounds — any field missing
        if force:
            where = "1=1"
        else:
            where = """COALESCE(rc.editor_status, 'pending') != 'approved'
              AND (rc.resource_id IS NULL
                   OR rc.tagline IS NULL OR rc.tagline = ''
                   OR rc.ai_summary IS NULL OR rc.ai_summary = ''
                   OR rc.ai_keywords IS NULL OR rc.ai_keywords = ''
                   OR rc.ai_reason_candidates IS NULL OR rc.ai_reason_candidates = '')"""

    query = f"""
        SELECT r.res_id, r.title,
               COALESCE(r.category, '')   AS category,
               COALESCE(r.platform, '')   AS platform,
               COALESCE(r.version, '')    AS version,
               COALESCE(rc.ai_summary, '') AS ai_summary,
               COALESCE(r.seo_desc, '')   AS seo_desc,
               COALESCE(rc.resource_type, '') AS resource_type
        FROM resources r
        LEFT JOIN resource_content rc ON r.res_id = rc.resource_id
        WHERE {where}
        ORDER BY r.res_id
    """

    if limit:
        query += f" LIMIT {int(limit)}"

    return cursor.execute(query).fetchall()


def save_round1(cursor, resource_id, data, force=False):
    """保存 Round 1 内容到 resource_content.

    force=False: CASE 保护已有值不覆盖.
    force=True:  覆盖 AI 字段 (绝不动 editor_* 人工字段).
    """
    if force:
        cursor.execute("""
            INSERT INTO resource_content
                (resource_id, tagline, ai_summary, ai_keywords, ai_generated)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(resource_id) DO UPDATE SET
                tagline      = excluded.tagline,
                ai_summary   = excluded.ai_summary,
                ai_keywords  = excluded.ai_keywords,
                ai_generated = 1
        """, (resource_id, data["tagline"], data["ai_summary"], data["ai_keywords"]))
    else:
        cursor.execute("""
            INSERT INTO resource_content
                (resource_id, tagline, ai_summary, ai_keywords, ai_generated)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(resource_id) DO UPDATE SET
                tagline = CASE
                    WHEN resource_content.tagline IS NULL OR resource_content.tagline = ''
                    THEN excluded.tagline
                    ELSE resource_content.tagline
                END,
                ai_summary = CASE
                    WHEN resource_content.ai_summary IS NULL OR resource_content.ai_summary = ''
                    THEN excluded.ai_summary
                    ELSE resource_content.ai_summary
                END,
                ai_keywords = CASE
                    WHEN resource_content.ai_keywords IS NULL OR resource_content.ai_keywords = ''
                    THEN excluded.ai_keywords
                    ELSE resource_content.ai_keywords
                END,
                ai_generated = 1
        """, (resource_id, data["tagline"], data["ai_summary"], data["ai_keywords"]))


def save_round2(cursor, resource_id, ai_reason_candidates, force=False):
    """保存 Round 2 内容到 resource_content."""
    if force:
        cursor.execute("""
            INSERT INTO resource_content
                (resource_id, ai_reason_candidates, ai_generated)
            VALUES (?, ?, 1)
            ON CONFLICT(resource_id) DO UPDATE SET
                ai_reason_candidates = excluded.ai_reason_candidates,
                ai_generated = 1
        """, (resource_id, ai_reason_candidates))
    else:
        cursor.execute("""
            INSERT INTO resource_content
                (resource_id, ai_reason_candidates, ai_generated)
            VALUES (?, ?, 1)
            ON CONFLICT(resource_id) DO UPDATE SET
                ai_reason_candidates = CASE
                    WHEN resource_content.ai_reason_candidates IS NULL
                      OR resource_content.ai_reason_candidates = ''
                    THEN excluded.ai_reason_candidates
                    ELSE resource_content.ai_reason_candidates
                END,
                ai_generated = 1
        """, (resource_id, ai_reason_candidates))


# ============================================================
# 6. --plan 统计
# ============================================================

def cmd_plan():
    """统计各字段缺失量，不修改任何数据."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    total = cursor.execute("SELECT COUNT(*) FROM resources").fetchone()[0]

    # 基础查询: 排除 approved 资源
    base = """
        SELECT COUNT(*) FROM resources r
        LEFT JOIN resource_content rc ON r.res_id = rc.resource_id
        WHERE COALESCE(rc.editor_status, 'pending') != 'approved'
    """

    tagline_needed = cursor.execute(
        base + " AND (rc.resource_id IS NULL OR rc.tagline IS NULL OR rc.tagline = '')"
    ).fetchone()[0]

    summary_needed = cursor.execute(
        base + " AND (rc.resource_id IS NULL OR rc.ai_summary IS NULL OR rc.ai_summary = '')"
    ).fetchone()[0]

    keywords_needed = cursor.execute(
        base + " AND (rc.resource_id IS NULL OR rc.ai_keywords IS NULL OR rc.ai_keywords = '')"
    ).fetchone()[0]

    reason_needed = cursor.execute(
        base + " AND (rc.resource_id IS NULL OR rc.ai_reason_candidates IS NULL OR rc.ai_reason_candidates = '')"
    ).fetchone()[0]

    approved_count = cursor.execute(
        "SELECT COUNT(*) FROM resource_content WHERE editor_status = 'approved'"
    ).fetchone()[0]

    conn.close()

    print()
    print("=" * 55)
    print("  ai_seo_writer v2.0 — Generation Plan")
    print("=" * 55)
    print()
    print(f"  Total resources:       {total}")
    print(f"  Approved (locked):     {approved_count}")
    print()
    print("  Round 1 — needs generation:")
    print(f"    tagline:                {tagline_needed}")
    print(f"    ai_summary:             {summary_needed}")
    print(f"    ai_keywords:            {keywords_needed}")
    print()
    print("  Round 2 — needs generation:")
    print(f"    ai_reason_candidates:   {reason_needed}")
    print()
    print("  Suggested order:")
    if tagline_needed or summary_needed or keywords_needed:
        print(f"    1. python3 ai_seo_writer.py --round 1 --limit 10")
        print(f"    2. Check quality → adjust prompts")
        print(f"    3. python3 ai_seo_writer.py --round 1 --limit 100")
        print(f"    4. python3 ai_seo_writer.py --round 1")
    if reason_needed:
        print(f"    5. python3 ai_seo_writer.py --round 2 --limit 10")
        print(f"    6. python3 ai_seo_writer.py --round 2")
    print()


# ============================================================
# 6b. --audit 质量巡检
# ============================================================

# 营销腔检测词 (比 FORBIDDEN_WORDS 更广, 用于 audit 报告而非阻断)
AUDIT_MARKETING_WORDS = [
    "强大", "领先", "顶级", "最强", "最好", "第一", "神器",
    "无与伦比", "革命性", "颠覆性", "史无前例", "前所未有",
    "必备", "必装", "不容错过", "强烈推荐", "首选",
]

# 过于通用的关键词 (没有搜索价值)
GENERIC_KEYWORDS = [
    "软件", "工具", "资源", "应用", "程序", "平台", "系统",
    "免费", "好用", "实用", "推荐",
]

# 推荐理由里的广告腔
AD_REASON_PATTERNS = [
    "非常", "十分", "极其", "特别", "极为",
    "值得推荐", "强烈推荐", "不容错过",
]


def cmd_audit():
    """扫描 resource_content 中所有 AI 生成字段，输出质量报告."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    rows = cursor.execute("""
        SELECT r.res_id, r.title, r.category,
               rc.tagline, rc.ai_summary, rc.ai_keywords,
               rc.ai_reason_candidates, rc.editor_status
        FROM resource_content rc
        JOIN resources r ON r.res_id = rc.resource_id
        ORDER BY r.res_id
    """).fetchall()

    if not rows:
        print("⚠️  resource_content 表中无数据。请先运行 ai_seo_writer.py")
        conn.close()
        return

    total = len(rows)

    # ---- 统计容器 ----
    tagline_lens = []
    tagline_marketing = []    # (res_id, title, word)
    tagline_empty = 0

    summary_lens = []
    summary_over50 = []       # (res_id, title, len)
    summary_marketing = []    # (res_id, title, word)
    summary_empty = 0

    keywords_empty = 0
    keywords_few = []         # (res_id, title, count) — < 4 个
    keywords_generic = []     # (res_id, title, [generic_kw])

    reason_empty = 0
    reason_few = []           # (res_id, title, count) — < 3 条
    reason_ad = []            # (res_id, title, pattern)

    # ---- 逐行扫描 ----
    for row in rows:
        res_id, title, category, tagline, summary, keywords_raw, reason_raw, status = row

        # --- tagline ---
        if has_value(tagline):
            t = str(tagline).strip()
            tagline_lens.append(len(t))
            for w in AUDIT_MARKETING_WORDS:
                if w in t:
                    tagline_marketing.append((res_id, title, w))
                    break
        else:
            tagline_empty += 1

        # --- ai_summary ---
        if has_value(summary):
            s = str(summary).strip()
            summary_lens.append(len(s))
            if len(s) > 50:
                summary_over50.append((res_id, title, len(s)))
            for w in AUDIT_MARKETING_WORDS:
                if w in s:
                    summary_marketing.append((res_id, title, w))
                    break
        else:
            summary_empty += 1

        # --- ai_keywords ---
        if has_value(keywords_raw):
            try:
                kw_list = json.loads(str(keywords_raw))
            except (json.JSONDecodeError, TypeError):
                kw_list = []

            if len(kw_list) < 4:
                keywords_few.append((res_id, title, len(kw_list)))

            generic_found = [kw for kw in kw_list if kw in GENERIC_KEYWORDS]
            if generic_found:
                keywords_generic.append((res_id, title, generic_found))
        else:
            keywords_empty += 1

        # --- ai_reason_candidates ---
        if has_value(reason_raw):
            try:
                rc_list = json.loads(str(reason_raw))
            except (json.JSONDecodeError, TypeError):
                rc_list = []

            if len(rc_list) < 3:
                reason_few.append((res_id, title, len(rc_list)))

            reason_text = " ".join(rc_list)
            for pat in AD_REASON_PATTERNS:
                if pat in reason_text:
                    reason_ad.append((res_id, title, pat))
                    break
        else:
            reason_empty += 1

    conn.close()

    # ---- 报告输出 ----
    filled = total - tagline_empty
    avg_tag = sum(tagline_lens) / len(tagline_lens) if tagline_lens else 0
    avg_sum = sum(summary_lens) / len(summary_lens) if summary_lens else 0

    print()
    print("=" * 60)
    print("  BigPRC AI Content Audit")
    print("=" * 60)
    print(f"  Scanned: {total} resources")
    print()

    # -- tagline --
    print("─" * 60)
    print("  📝 tagline")
    print(f"    已填: {filled}/{total}  "
          f"空: {tagline_empty}  "
          f"平均长度: {avg_tag:.1f} 字")
    if tagline_marketing:
        print(f"    ⚠️  营销词: {len(tagline_marketing)} 条")
        for rid, t, w in tagline_marketing[:5]:
            print(f"       {rid} {t[:30]}  → \"{w}\"")
        if len(tagline_marketing) > 5:
            print(f"       ... +{len(tagline_marketing) - 5} more")
    else:
        print(f"    ✅ 无营销词")

    # -- ai_summary --
    print()
    print("─" * 60)
    print("  📄 ai_summary")
    print(f"    已填: {total - summary_empty}/{total}  "
          f"空: {summary_empty}  "
          f"平均长度: {avg_sum:.1f} 字")
    if summary_over50:
        print(f"    ⚠️  超 50 字: {len(summary_over50)} 条")
        for rid, t, l in summary_over50[:5]:
            print(f"       {rid} {t[:30]}  → {l} 字")
        if len(summary_over50) > 5:
            print(f"       ... +{len(summary_over50) - 5} more")
    else:
        print(f"    ✅ 全部 ≤50 字")
    if summary_marketing:
        print(f"    ⚠️  营销词: {len(summary_marketing)} 条")
        for rid, t, w in summary_marketing[:5]:
            print(f"       {rid} {t[:30]}  → \"{w}\"")
    else:
        print(f"    ✅ 无营销词")

    # -- ai_keywords --
    print()
    print("─" * 60)
    print("  🔑 ai_keywords")
    print(f"    已填: {total - keywords_empty}/{total}  "
          f"空: {keywords_empty}")
    if keywords_few:
        print(f"    ⚠️  <4 个关键词: {len(keywords_few)} 条")
        for rid, t, c in keywords_few[:5]:
            print(f"       {rid} {t[:30]}  → {c} 个")
    else:
        print(f"    ✅ 全部 ≥4 个关键词")
    if keywords_generic:
        print(f"    ⚠️  含通用词: {len(keywords_generic)} 条")
        for rid, t, kws in keywords_generic[:5]:
            print(f"       {rid} {t[:30]}  → {kws}")
        if len(keywords_generic) > 5:
            print(f"       ... +{len(keywords_generic) - 5} more")
    else:
        print(f"    ✅ 无通用关键词")

    # -- ai_reason_candidates --
    print()
    print("─" * 60)
    print("  💬 ai_reason_candidates")
    print(f"    已填: {total - reason_empty}/{total}  "
          f"空: {reason_empty}")
    if reason_few:
        print(f"    ⚠️  <3 条理由: {len(reason_few)} 条")
        for rid, t, c in reason_few[:5]:
            print(f"       {rid} {t[:30]}  → {c} 条")
    else:
        print(f"    ✅ 全部 ≥3 条理由")
    if reason_ad:
        print(f"    ⚠️  广告腔: {len(reason_ad)} 条")
        for rid, t, p in reason_ad[:5]:
            print(f"       {rid} {t[:30]}  → \"{p}\"")
        if len(reason_ad) > 5:
            print(f"       ... +{len(reason_ad) - 5} more")
    else:
        print(f"    ✅ 无广告腔")

    # -- 总评 --
    issue_count = (
        len(tagline_marketing) + len(summary_over50) + len(summary_marketing) +
        len(keywords_few) + len(keywords_generic) +
        len(reason_few) + len(reason_ad)
    )
    print()
    print("─" * 60)
    if issue_count == 0:
        print("  🎉 ALL CLEAN — 未发现质量问题")
    else:
        print(f"  📊 共发现 {issue_count} 个问题 (详情见上)")
    print("=" * 60)
    print()


# ============================================================
# 7. 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="BigPRC ai_seo_writer v2.0 — AI content generator for resource_content"
    )
    parser.add_argument("--plan", action="store_true",
                        help="Show pending counts and exit")
    parser.add_argument("--audit", action="store_true",
                        help="Scan all AI content for quality issues")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max resources to process (default: all)")
    parser.add_argument("--round", type=int, choices=[1, 2], default=None,
                        help="Round to run (1=basic, 2=reasons, default=both)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing AI content")
    parser.add_argument("--resume", action="store_true",
                        help="Skip already-filled fields (this is the default)")

    args = parser.parse_args()

    # ---- Plan mode ----
    if args.plan:
        cmd_plan()
        return

    # ---- Audit mode ----
    if args.audit:
        cmd_audit()
        return

    # ---- Normal mode ----
    rounds_to_run = [args.round] if args.round else [1, 2]
    force = args.force
    limit = args.limit
    round_label = f"Round {args.round}" if args.round else "Round 1+2"

    print(f"🚀 ai_seo_writer v2.0 | {round_label} | "
          f"{'FORCE' if force else 'protect'}")
    print(f"   DB:    {DB_FILE}")
    print(f"   Limit: {limit if limit else 'all'}")
    print()

    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    stats = {
        "r1_gen": 0, "r1_fail": 0, "r1_skip": 0,
        "r2_gen": 0, "r2_fail": 0, "r2_skip": 0,
    }

    for round_num in rounds_to_run:
        resources = get_pending_resources(cursor, round_num, force=force, limit=limit)

        if not resources:
            print(f"✅ Round {round_num}: nothing to generate.")
            continue

        print(f"📋 Round {round_num}: {len(resources)} resources")
        print()

        for idx, row in enumerate(resources, 1):
            res_id   = row[0]
            title    = row[1]
            category = row[2] or ""
            platform = row[3] or ""
            version  = row[4] or ""
            summary  = row[5] or ""
            seo_desc = row[6] or ""
            res_type = row[7] or ""

            print(f"[{idx}/{len(resources)}] {res_id}  {title[:55]}")

            # ---- Round 1 ----
            if round_num == 1:
                # 逐字段判断 (即使 get_pending_resources 已粗筛, 这里做细粒度跳过)
                needed = {
                    'tagline':     should_generate_field(cursor, res_id, 'tagline', force),
                    'ai_summary':  should_generate_field(cursor, res_id, 'ai_summary', force),
                    'ai_keywords': should_generate_field(cursor, res_id, 'ai_keywords', force),
                }
                if not any(needed.values()):
                    print(f"   ⏭️  all fields filled")
                    stats["r1_skip"] += 1
                else:
                    data = generate_round1(title, category, platform, version, seo_desc, res_type)
                    if data:
                        save_round1(cursor, res_id, data, force=force)
                        conn.commit()
                        stats["r1_gen"] += 1
                        summary = data["ai_summary"]  # 传给 Round 2 使用
                        print(f"   ✅ tagline={data['tagline']}  (conf={data['confidence']:.0%})")
                    else:
                        stats["r1_fail"] += 1

            # ---- Round 2 ----
            if round_num == 2:
                if not should_generate_field(cursor, res_id, 'ai_reason_candidates', force):
                    print(f"   ⏭️  reason_candidates filled")
                    stats["r2_skip"] += 1
                else:
                    reasons = generate_round2(title, category, platform, summary, seo_desc, res_type)
                    if reasons:
                        save_round2(cursor, res_id, reasons, force=force)
                        conn.commit()
                        stats["r2_gen"] += 1
                        print(f"   ✅ reason_candidates saved")
                    else:
                        stats["r2_fail"] += 1

            # 速率限制 + 定期提交
            if idx % 5 == 0:
                conn.commit()
            time.sleep(0.5)

    conn.commit()
    conn.close()

    # ---- 报告 ----
    print()
    print("=" * 55)
    print("  Generation Report")
    print("=" * 55)
    if 1 in rounds_to_run:
        print(f"  Round 1: ✅ {stats['r1_gen']} gen  "
              f"⏭️  {stats['r1_skip']} skip  "
              f"❌ {stats['r1_fail']} fail")
    if 2 in rounds_to_run:
        print(f"  Round 2: ✅ {stats['r2_gen']} gen  "
              f"⏭️  {stats['r2_skip']} skip  "
              f"❌ {stats['r2_fail']} fail")
    print("=" * 55)


if __name__ == "__main__":
    main()
