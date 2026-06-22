#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# bigprc.com 死链自动检测脚本
# 检查数据库中所有第三方网盘链接是否存活
#
# 部署: 添加到 crontab (每周一凌晨 3 点)
#   crontab -e
#   0 3 * * 1 /usr/bin/python3 /root/scripts/check_dead_links.py
#
# 输出: /root/scripts/dead_links_report.txt
# ============================================================
import os
import sys
import sqlite3
import requests
import time
import re
from datetime import datetime
from dotenv import load_dotenv

# Load config
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

DB_FILE = os.getenv("DB_FILE", "/root/scripts/database.db")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@bigprc.com")
REPORT_FILE = os.path.join(script_dir, "dead_links_report.txt")
LOG_FILE = os.path.join(script_dir, "dead_links_check.log")

# Dead link detection patterns (present in HTTP response body)
DEAD_PATTERNS = [
    "分享已取消", "文件已删除", "链接不存在", "页面不存在",
    "已失效", "该分享已被取消", "你来晚了", "已被删除",
    "已过期", "已下架", "链接失效", "分享已过期",
    "该链接已失效", "此链接已失效", "资源已删除",
    "分享的文件已经被取消了", "分享的文件已经被删除",
    "啊哦，你来晚了", "分享的文件不存在",
    "404", "页面找不到了", "Not Found"
]

# Alive indicators (to reduce false positives)
ALIVE_PATTERNS = [
    "请输入提取码", "提取码", "文件大小", "下载",
    "保存到网盘", "转存", "下载次数", "浏览次数",
    "pan.baidu.com/s/", "quark.cn/s/", "alipan.com/s/"
]

REQUEST_TIMEOUT = 20
REQUEST_DELAY = 1.5  # seconds between requests (avoid rate limiting)
BATCH_SIZE = 50      # report progress every N items

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def check_url(url, res_id, title):
    """Check if a single URL is alive. Returns (status, detail)."""
    if not url or url.strip().lower() in ("none", "null", ""):
        return "skip", "no URL"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    try:
        # HEAD first (faster, less bandwidth)
        r = requests.head(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        status_code = r.status_code

        if status_code == 200:
            # Quick content check via GET (first 8KB only)
            r2 = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True)
            content = ""
            for chunk in r2.iter_content(chunk_size=4096):
                content += chunk.decode("utf-8", errors="ignore")
                if len(content) > 8000:
                    break
            r2.close()

            for pattern in DEAD_PATTERNS:
                if pattern in content:
                    return "dead", f"HTTP 200 but body contains '{pattern}'"

            for pattern in ALIVE_PATTERNS:
                if pattern in content:
                    return "alive", "confirmed"

            return "uncertain", f"HTTP 200 but no clear indicator"

        elif status_code in (301, 302, 303, 307, 308):
            return "alive", f"HTTP {status_code} redirect"

        elif status_code in (403, 429):
            return "uncertain", f"HTTP {status_code} (rate-limited or geo-blocked)"

        elif status_code in (404, 410, 451):
            return "dead", f"HTTP {status_code}"

        else:
            return "uncertain", f"HTTP {status_code}"

    except requests.exceptions.Timeout:
        return "uncertain", "timeout"
    except requests.exceptions.ConnectionError:
        return "dead", "connection failed (DNS/down)"
    except requests.exceptions.SSLError:
        return "uncertain", "SSL error"
    except Exception as e:
        return "error", str(e)[:100]

def main():
    log("====== 死链检测开始 ======")

    if not os.path.exists(DB_FILE):
        log(f"ERROR: 数据库不存在: {DB_FILE}")
        sys.exit(1)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT res_id, title, normal_url, short_url FROM resources")
    rows = cursor.fetchall()
    conn.close()

    total = len(rows)
    log(f"共 {total} 条资源待检测")

    dead_links = []
    uncertain_links = []
    alive_count = 0
    skip_count = 0

    for i, (res_id, title, normal_url, short_url) in enumerate(rows):
        urls_to_check = [(normal_url, "normal"), (short_url, "short")]
        for url, url_type in urls_to_check:
            if not url or str(url).strip().lower() in ("none", "null", ""):
                continue

            status, detail = check_url(url, res_id, title)

            if status == "dead":
                dead_links.append((res_id, title, url_type, url, detail))
                log(f"  💀 DEAD  [{res_id}] {title[:40]} ({url_type}): {detail}")
            elif status == "uncertain":
                uncertain_links.append((res_id, title, url_type, url, detail))
            elif status == "alive":
                alive_count += 1
            else:
                skip_count += 1

            time.sleep(REQUEST_DELAY)

        # Progress report
        if (i + 1) % BATCH_SIZE == 0:
            log(f"  进度: {i+1}/{total} (死链: {len(dead_links)}, 存活: {alive_count})")

    # Write report
    report = []
    report.append(f"BigPRC 死链检测报告")
    report.append(f"检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"检测总量: {total} 条资源")
    report.append(f"=" * 60)
    report.append(f"")
    report.append(f"💀 确认死链: {len(dead_links)} 条")
    report.append(f"⚠️  状态不确定: {len(uncertain_links)} 条")
    report.append(f"✅ 确认存活: {alive_count} 条")
    report.append(f"")
    report.append("=" * 60)
    report.append("")

    if dead_links:
        report.append("## 死链详情")
        report.append("")
        for res_id, title, url_type, url, detail in dead_links:
            report.append(f"  [{res_id}] {title[:50]}")
            report.append(f"    URL类型: {url_type}")
            report.append(f"    URL: {url[:100]}")
            report.append(f"    原因: {detail}")
            report.append("")

    if uncertain_links:
        report.append("## 状态不确定 (建议人工复核)")
        report.append("")
        for res_id, title, url_type, url, detail in uncertain_links:
            report.append(f"  [{res_id}] {title[:50]} - {url_type}: {detail}")
        report.append("")

    report_text = "\n".join(report)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    log(f"====== 检测完成 =====")
    log(f"死链: {len(dead_links)}, 不确定: {len(uncertain_links)}, 存活: {alive_count}")
    log(f"报告: {REPORT_FILE}")

    # Email report if dead links found
    if dead_links and os.system("which mail > /dev/null 2>&1") == 0:
        subject = f"[BigPRC] 死链检测报告 — {len(dead_links)} 条失效"
        cmd = f'echo "{report_text[:2000]}" | mail -s "{subject}" {ADMIN_EMAIL}'
        os.system(cmd)
        log(f"邮件已发送到 {ADMIN_EMAIL}")

    return len(dead_links)

if __name__ == "__main__":
    dead_count = main()
    sys.exit(0 if dead_count == 0 else 1)
