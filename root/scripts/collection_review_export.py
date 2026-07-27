#!/usr/bin/env python3
"""BigPRC Collection Review Exporter — 一键生成编辑审核数据.

python3 collection_review_export.py
  → Discovery → Gap → /var/www/site/web/admin/data/review-data.json
"""

import os, sys, json, subprocess, shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = "/var/www/site/web/admin/data"

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("🔍 Running Discovery...")
    disc = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "collection_discovery.py"), "--scan", "--json"],
        capture_output=True, text=True, cwd=SCRIPT_DIR)
    if disc.returncode != 0:
        print(f"❌ Discovery failed:\n{disc.stderr}")
        sys.exit(1)
    discovery_json = disc.stdout

    print("📊 Running Gap Analyzer...")
    gap = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "collection_gap.py"), "--analyze", "--json"],
        input=discovery_json, capture_output=True, text=True, cwd=SCRIPT_DIR)
    if gap.returncode != 0:
        print(f"❌ Gap Analyzer failed:\n{gap.stderr}")
        sys.exit(1)

    out_path = os.path.join(OUT_DIR, "review-data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(gap.stdout)

    print(f"✅ Exported to {out_path}")
    print(f"   Size: {os.path.getsize(out_path)} bytes")


if __name__ == "__main__":
    main()
