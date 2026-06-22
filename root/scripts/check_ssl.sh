#!/usr/bin/env bash
# ============================================================
# bigprc.com SSL 证书过期检查脚本
# 检查 Let's Encrypt 证书剩余有效期，< 14 天发送告警
#
# 部署: 添加到 crontab (每天上午 9 点运行一次)
#   crontab -e
#   0 9 * * * /root/scripts/check_ssl.sh
#
# 依赖: openssl (Ubuntu 默认已安装)
#        mailutils (可选，用于邮件告警: apt install mailutils)
# ============================================================
set -euo pipefail

DOMAIN="${DOMAIN:-www.bigprc.com}"
CERT_FILE="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
THRESHOLD_DAYS="${THRESHOLD_DAYS:-14}"
LOG_FILE="${LOG_FILE:-/root/scripts/ssl_check.log}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@bigprc.com}"

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

if [ ! -f "$CERT_FILE" ]; then
    log_msg "ERROR: 证书文件不存在: $CERT_FILE"
    # Also check for wildcard or alternate domains
    if [ -d "/etc/letsencrypt/live" ]; then
        log_msg "INFO: 可用的证书目录:"
        ls -la /etc/letsencrypt/live/ >> "$LOG_FILE" 2>&1
    fi
    exit 1
fi

# Get cert expiry date
# Ubuntu date supports -d flag for date parsing
END_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
END_EPOCH=$(date -d "$END_DATE" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$END_DATE" +%s 2>/dev/null)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( (END_EPOCH - NOW_EPOCH) / 86400 ))

log_msg "域名: $DOMAIN"
log_msg "证书到期日: $END_DATE"
log_msg "剩余天数: $DAYS_LEFT"

if [ "$DAYS_LEFT" -le 0 ]; then
    log_msg "CRITICAL: SSL 证书已过期！请立即运行 certbot renew"
    if command -v mail &>/dev/null; then
        echo "SSL 证书 $DOMAIN 已过期！到期日: $END_DATE。请立即运行 certbot renew。" | \
            mail -s "[紧急] BigPRC SSL 证书已过期" "$ADMIN_EMAIL"
    fi
    exit 2
elif [ "$DAYS_LEFT" -le "$THRESHOLD_DAYS" ]; then
    log_msg "WARNING: SSL 证书将在 $DAYS_LEFT 天后过期 (告警阈值: $THRESHOLD_DAYS 天)"
    log_msg "建议运行: certbot renew --dry-run"
    if command -v mail &>/dev/null; then
        echo "SSL 证书 $DOMAIN 将在 $DAYS_LEFT 天后过期。到期日: $END_DATE。建议运行 certbot renew。" | \
            mail -s "[警告] BigPRC SSL 证书即将过期 ($DAYS_LEFT 天)" "$ADMIN_EMAIL"
    else
        log_msg "INFO: mail 命令不可用，跳过邮件告警 (apt install mailutils)"
    fi
    exit 0
else
    log_msg "OK: 证书状态正常 (> $THRESHOLD_DAYS 天)"
fi
