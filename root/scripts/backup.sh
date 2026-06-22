#!/usr/bin/env bash
# ============================================================
# bigprc.com 数据备份脚本
# 备份: Excel数据 + SQLite数据库 + Nginx配置 + 模板 + 自定义页面
# 保留: 最近 7 天的备份 (可通过 RETENTION_DAYS 调整)
#
# 部署: 添加到 crontab (每天凌晨 2 点运行)
#   crontab -e
#   0 2 * * * /root/scripts/backup.sh
#
# 远程备份 (可选):
#   REMOTE_UPLOAD="user@backup.example.com:/backups/bigprc" /root/scripts/backup.sh
#   或在 crontab 中设置:
#   0 2 * * * REMOTE_UPLOAD="user@host:/path" /root/scripts/backup.sh
#
# 恢复备份:
#   cd /root/backups
#   tar xzf bigprc_backup_YYYYMMDD_HHMMSS.tar.gz -C /tmp/restore/
#   然后手动复制恢复的文件到目标位置
# ============================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/root/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
REMOTE_UPLOAD="${REMOTE_UPLOAD:-}"
LOG_FILE="${LOG_FILE:-/root/scripts/backup.log}"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_NAME="bigprc_backup_${TIMESTAMP}.tar.gz"
MAX_LOG_LINES=500

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Rotate log if too large
if [ -f "$LOG_FILE" ]; then
    LINE_COUNT=$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "$LINE_COUNT" -gt "$MAX_LOG_LINES" ]; then
        tail -n "$MAX_LOG_LINES" "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
    fi
fi

log_msg "====== 开始备份 ======"

mkdir -p "$BACKUP_DIR"

# Create temp working directory
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# 1. Data files
log_msg "收集数据文件..."
if [ -f /root/scripts/pantools_export.xlsx ]; then
    cp /root/scripts/pantools_export.xlsx "$TEMP_DIR/"
    log_msg "  -> pantools_export.xlsx"
else
    log_msg "  WARN: pantools_export.xlsx 不存在"
fi

if [ -f /root/scripts/database.db ]; then
    cp /root/scripts/database.db "$TEMP_DIR/"
    log_msg "  -> database.db"
else
    log_msg "  WARN: database.db 不存在"
fi

if [ -f /root/scripts/.env ]; then
    cp /root/scripts/.env "$TEMP_DIR/"
    log_msg "  -> .env"
fi

# 2. Nginx configs
log_msg "收集 Nginx 配置..."
if [ -d /root/bigprc-deploy/etc/nginx ]; then
    mkdir -p "$TEMP_DIR/nginx"
    cp -r /root/bigprc-deploy/etc/nginx/* "$TEMP_DIR/nginx/" 2>/dev/null || true
    log_msg "  -> nginx configs"
fi

# 3. Custom pages
log_msg "收集自定义页面..."
if [ -d /root/bigprc-deploy/root/custom-pages ]; then
    cp -r /root/bigprc-deploy/root/custom-pages "$TEMP_DIR/custom-pages" 2>/dev/null || true
    log_msg "  -> custom pages"
fi

# 4. Templates
log_msg "收集模板文件..."
if [ -d /root/scripts/templates ]; then
    cp -r /root/scripts/templates "$TEMP_DIR/templates" 2>/dev/null || true
    log_msg "  -> templates"
fi

# 5. Create archive
log_msg "创建压缩包..."
cd "$TEMP_DIR"
tar czf "$BACKUP_DIR/$BACKUP_NAME" .

if [ -f "$BACKUP_DIR/$BACKUP_NAME" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)
    log_msg "备份完成: $BACKUP_DIR/$BACKUP_NAME ($BACKUP_SIZE)"
else
    log_msg "ERROR: 压缩包创建失败"
    exit 1
fi

# 6. Clean up old backups
log_msg "清理 $RETENTION_DAYS 天前的旧备份..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "bigprc_backup_*.tar.gz" -mtime "+${RETENTION_DAYS}" -delete -print 2>/dev/null | wc -l)
if [ "$DELETED_COUNT" -gt 0 ]; then
    log_msg "已清理 $DELETED_COUNT 个过期备份"
else
    log_msg "无过期备份需要清理"
fi

# 7. Show remaining backup count
REMAINING_COUNT=$(find "$BACKUP_DIR" -name "bigprc_backup_*.tar.gz" | wc -l)
log_msg "当前保留 $REMAINING_COUNT 个备份"

# 8. Optional remote upload
if [ -n "$REMOTE_UPLOAD" ]; then
    log_msg "上传到远程: $REMOTE_UPLOAD"
    if rsync -az "$BACKUP_DIR/$BACKUP_NAME" "$REMOTE_UPLOAD/" 2>/dev/null; then
        log_msg "远程上传成功"
    else
        log_msg "WARNING: 远程上传失败 (检查 rsync 和远程路径)"
    fi
fi

log_msg "====== 备份结束 ======"
