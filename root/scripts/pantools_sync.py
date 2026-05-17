# -*- coding: utf-8 -*-
import os
import sqlite3
import openpyxl
from dotenv import load_dotenv

# 1. 加载机密配置
load_dotenv("/root/scripts/.env")
EXCEL_FILE = os.getenv("EXCEL_FILE")
DB_FILE = os.getenv("DB_FILE")

def init_db():
    """初始化 SQLite 数据库表结构"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 创建资源主表 (具备防重复机制)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            res_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            size TEXT,
            normal_url TEXT,
            short_url TEXT,
            seo_desc TEXT,
            sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def sync_excel_to_db(conn):
    """将 Excel 数据清洗并洗入 SQLite"""
    print(f"📥 正在读取数据源: {EXCEL_FILE}")
    try:
        wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
        sheet = wb.active
        header = {cell.value.strip(): idx for idx, cell in enumerate(sheet[1]) if cell.value}
    except Exception as e:
        print(f"❌ Excel 读取失败: {e}")
        return

    cursor = conn.cursor()
    row_num = 1
    insert_count = 0
    update_count = 0

    for row in sheet.iter_rows(min_row=2, values_only=True):
        title = row[header.get("文件名")]
        if not title: continue
        
        # 数据清洗
        title_str = str(title).strip()
        normal_url = str(row[header.get("链接")]).strip() if row[header.get("链接")] else None
        short_url = str(row[header.get("短链")]).strip() if "短链" in header and row[header.get("短链")] else None
        raw_size = row[header.get("文件大小")] if "文件大小" in header else None
        size = "N/A" if (raw_size is None or str(raw_size).strip().lower() in ["", "none", "-"]) else str(raw_size).strip()
        seo_desc = row[header.get("SEO简介")] if "SEO简介" in header else ""
        if not seo_desc or str(seo_desc).strip() in ["None", ""]:
            seo_desc = "极客精选优质资源，全网稀缺，无广告纯净版，推荐直接转存。"

        if normal_url == "None": normal_url = None
        if short_url == "None": short_url = None
        if not normal_url and not short_url: continue

        res_id = f"p{row_num:03d}"
        
        # 尝试插入或更新数据 (UPSERT 语法，极速排重)
        cursor.execute('''
            INSERT INTO resources (res_id, title, size, normal_url, short_url, seo_desc)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(res_id) DO UPDATE SET
                title=excluded.title,
                size=excluded.size,
                normal_url=excluded.normal_url,
                short_url=excluded.short_url,
                seo_desc=excluded.seo_desc,
                sync_time=CURRENT_TIMESTAMP
        ''', (res_id, title_str, size, normal_url, short_url, seo_desc))
        
        if cursor.rowcount == 1:
            insert_count += 1
        else:
            update_count += 1
            
        row_num += 1

    conn.commit()
    print(f"✅ 数据清洗完成！SQLite 数据库已更新。")
    print(f"📊 统计: 新增 {insert_count} 条，更新 {update_count} 条，总计库内容量: {insert_count + update_count} 条。")

if __name__ == "__main__":
    db_conn = init_db()
    sync_excel_to_db(db_conn)
    db_conn.close()
