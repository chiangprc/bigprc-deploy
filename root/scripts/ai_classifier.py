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

# resource_type 枚举 (英文标签, 前端映射为中文)
VALID_TYPES = {
    "NatureDocumentary", "WildlifeDoc", "EarthScience", "OceanDoc", "SpaceDoc",
    "HistoryDocumentary", "WarDoc", "CivilizationDoc", "ReligionDoc", "PhilosophyText",
    "TravelDocumentary", "GeographyDoc", "CityDoc", "RailwayDoc",
    "ArchitectureDoc", "ArtDocumentary", "MusicDoc", "DesignCourse", "PhotographyBook",
    "UtilitySoftware", "ProductivityApp", "Plugin", "IDE",
    "DevTool", "OpenSourceProject", "CodeLibrary", "Framework", "GitHubRepo",
    "AITool", "AIModel", "AICourse", "PromptSet",
    "MarketingCourse", "BusinessBook", "OperationsTool",
    "VideoCourse", "Tutorial", "Textbook", "SkillTraining",
    "Dictionary", "LiteratureCollection", "ReferenceBook", "ClassicText",
    "PCGame", "GameMod", "SimulationGame",
    "KidsAnimation", "EducationalVideo", "ChildrensBook",
    "TaoistText", "BuddhistScripture", "ClassicalLiterature", "TraditionalMedicine",
    "Other",
}

# 英文→中文映射 (前端展示用)
CATEGORY_CN = {
    "NaturalScience":   "自然科学",
    "HistoryCulture":   "历史文化",
    "TravelGeography":  "旅行地理",
    "ArtDesign":        "艺术设计",
    "FoodLifestyle":    "美食生活",
    "SoftwareTool":     "软件工具",
    "DevProgramming":   "编程开发",
    "AITech":           "AI技术",
    "DesignCreative":   "设计创意",
    "BusinessCareer":   "商业职场",
    "StudyCourse":      "课程学习",
    "EbookRead":        "电子书籍",
    "GamePlay":         "游戏娱乐",
    "KidsEducation":    "儿童教育",
    "ChineseCulture":   "传统文化",
    "Other":            "其他",
}

PLATFORM_CN = {
    "Windows":       "Windows",
    "Mac":           "Mac",
    "Linux":         "Linux",
    "Web":           "网页",
    "iOS":           "iOS",
    "Android":       "Android",
    "CrossPlatform": "跨平台",
    "Video":         "视频",
    "PDF":           "PDF",
    "Ebook":         "电子书",
    "Audio":         "音频",
    "Image":         "图片",
    "Other":         "其他",
}

# 文件扩展名 → platform 映射 (优先于 AI 判断)
EXT_PLATFORM = {
    ".pdf":  "PDF",
    ".epub": "Ebook",
    ".mobi": "Ebook",
    ".azw3": "Ebook",
    ".djvu": "Ebook",
    ".doc":  "PDF",
    ".docx": "PDF",
    ".txt":  "PDF",
    ".xls":  "PDF",
    ".xlsx": "PDF",
    ".ppt":  "PDF",
    ".pptx": "PDF",
    ".cbr":  "Ebook",
    ".cbz":  "Ebook",
    ".chm":  "Ebook",
    ".zip":  "Other",
    ".rar":  "Other",
    ".7z":   "Other",
    ".tar":  "Other",
    ".gz":   "Other",
    ".apk":  "Android",
    ".exe":  "Windows",
    ".msi":  "Windows",
    ".dmg":  "Mac",
    ".pkg":  "Mac",
    ".deb":  "Linux",
    ".iso":  "Other",
    ".mp4":  "Video",
    ".mkv":  "Video",
    ".avi":  "Video",
    ".mov":  "Video",
    ".mp3":  "Audio",
    ".flac": "Audio",
    ".wav":  "Audio",
    ".jpg":  "Image",
    ".png":  "Image",
    ".gif":  "Image",
    ".webp": "Image",
    ".psd":  "Image",
}


def detect_platform_from_title(title):
    """根据文件名扩展名检测 platform，覆盖 AI 误判 (docx→PDF 等)."""
    if not title:
        return None
    t = title.lower().rstrip(")")
    for ext, plat in EXT_PLATFORM.items():
        if t.endswith(ext) or (ext + ")") in t:
            return plat
    return None

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


def get_unclassified(cursor, force=False, limit=None, random_order=False):
    """查询待分类的资源."""
    if force:
        where = "1=1"
    else:
        where = "(r.category IS NULL OR r.category = '' OR r.platform IS NULL OR r.platform = '')"

    order = "RANDOM()" if random_order else "r.res_id"

    query = f"""
        SELECT r.res_id, r.title, COALESCE(r.seo_desc, '') AS seo_desc,
               COALESCE(r.category, '') AS category,
               COALESCE(r.platform, '') AS platform
        FROM resources r
        WHERE {where}
        ORDER BY {order}
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
    """构造分类 prompt (v4: category = user browsing intent, not file type)."""
    parts = [f"Title: {title}"]
    if seo_desc:
        parts.append(f"Description: {seo_desc[:300]}")
    context = "\n".join(parts)

    return f"""Classify this digital resource for a curated content library. The goal is to help users DISCOVER resources, not just label them.

{context}

Output JSON with three DISTINCT fields (category and resource_type must NOT be the same):

1. category — the BROWSING shelf a user would look under. Pick ONE:
   NaturalScience (自然/地球/动物/生态/海洋/宇宙/环境)
   HistoryCulture (历史/文明/战争/考古/人文/哲学/宗教)
   TravelGeography (旅行/地理/探险/城市/铁路)
   ArtDesign (艺术/建筑/绘画/音乐/摄影/设计)
   FoodLifestyle (美食/生活/园艺/手工/健康)
   SoftwareTool (软件/应用/工具/插件)
   DevProgramming (编程/开发/GitHub/开源/框架)
   AITech (AI/机器学习/深度学习/大模型)
   DesignCreative (设计工具/创意/3D/视频编辑)
   BusinessCareer (商业/运营/营销/创业/管理)
   StudyCourse (课程/教程/学习/培训)
   EbookRead (电子书/书籍/词典/文献/小说)
   GamePlay (游戏/模组/MOD/模拟)
   KidsEducation (儿童/启蒙/动画/早教)
   ChineseCulture (国学/中医/道家/道教/佛教/古籍/传统文化)
   Other

2. platform — storage medium or access method:
   Windows / Mac / Linux / Web / iOS / Android / CrossPlatform /
   Video / PDF / Ebook / Audio / Image / Other

3. resource_type — specific subtype, must be DIFFERENT from category. Examples:
   For NaturalScience: NatureDocumentary / WildlifeDoc / EarthScience / OceanDoc / SpaceDoc
   For HistoryCulture: HistoryDocumentary / WarDoc / CivilizationDoc / ReligionDoc / PhilosophyText
   For TravelGeography: TravelDocumentary / GeographyDoc / CityDoc / RailwayDoc
   For ArtDesign: ArchitectureDoc / ArtDocumentary / MusicDoc / DesignCourse / PhotographyBook
   For SoftwareTool: UtilitySoftware / ProductivityApp / Plugin / IDE
   For DevProgramming: DevTool / OpenSourceProject / CodeLibrary / Framework / GitHubRepo
   For AITech: AITool / AIModel / AICourse / PromptSet
   For BusinessCareer: MarketingCourse / BusinessBook / OperationsTool
   For StudyCourse: VideoCourse / Tutorial / Textbook / SkillTraining
   For EbookRead: Dictionary / LiteratureCollection / ReferenceBook / ClassicText
   For GamePlay: PCGame / GameMod / SimulationGame
   For KidsEducation: KidsAnimation / EducationalVideo / ChildrensBook
   For ChineseCulture: TaoistText / BuddhistScripture / ClassicalLiterature / TraditionalMedicine
   For Other: Other

Rules (IMPORTANT):
- category and resource_type MUST be different! Never output Documentary for both.
- BBC Planet Earth is about nature -> category=NaturalScience, resource_type=NatureDocumentary
- BBC Empire is about history -> category=HistoryCulture, resource_type=HistoryDocumentary
- BBC Bombay Railway is about railways/travel -> category=TravelGeography, resource_type=RailwayDoc
- Taoist PDF manuscripts -> category=ChineseCulture, resource_type=TaoistText
- A video editing course -> category=StudyCourse, resource_type=VideoCourse
- A Windows ZIP tool -> category=SoftwareTool, resource_type=UtilitySoftware
- A children's English learning animation -> category=KidsEducation, resource_type=KidsAnimation
- Use the Description field (seo_desc) to understand what the resource is ABOUT, not just its format

JSON only:
{{"category":"NaturalScience","platform":"Video","resource_type":"NatureDocumentary"}}"""


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

        category = str(data.get("category", "Other")).strip()
        platform_ai = str(data.get("platform", "Other")).strip()
        resource_type = str(data.get("resource_type", "Other")).strip()

        # 扩展名检测覆盖 AI 的 platform (docx → PDF, apk → Android)
        platform_ext = detect_platform_from_title(title)
        platform = platform_ext if platform_ext else platform_ai

        if resource_type not in VALID_TYPES:
            resource_type = "Other"

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
    parser.add_argument("--random", action="store_true", help="Random order (for diverse sampling)")
    parser.add_argument("--force", action="store_true", help="Re-classify all, overwrite existing")
    args = parser.parse_args()

    if args.plan:
        cmd_plan()
        return

    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    ensure_columns(cursor)

    resources = get_unclassified(cursor, force=args.force, limit=args.limit, random_order=args.random)

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
