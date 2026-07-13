#!/usr/bin/env bash
# ============================================================
# bigprc VPS 结构审计脚本
# 运行方式: ssh 到 VPS 后执行，或复制粘贴逐段执行
# 输出方式: 全部跑完后把结果贴给 Claude
# ============================================================
set -euo pipefail

echo "=============================================="
echo "SECTION 1: Nginx 实际启用的站点"
echo "=============================================="
echo "--- 1a. sites-enabled 文件列表 ---"
ls -la /etc/nginx/sites-enabled/

echo "--- 1b. sites-available 文件列表 ---"
ls -la /etc/nginx/sites-available/

echo "--- 1c. Nginx 语法测试 ---"
nginx -t 2>&1

echo "--- 1d. Nginx 运行状态 ---"
systemctl status nginx --no-pager 2>&1 || service nginx status 2>&1

echo ""
echo "=============================================="
echo "SECTION 2: 监听端口 & 运行服务"
echo "=============================================="
echo "--- 2a. 所有监听端口 ---"
ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null

echo "--- 2b. :18789 是什么进程 ---"
ss -tlnp 2>/dev/null | grep 18789 || netstat -tlnp 2>/dev/null | grep 18789
echo "--- :3000 是什么进程 ---"
ss -tlnp 2>/dev/null | grep ':3000 ' || netstat -tlnp 2>/dev/null | grep ':3000 ' || echo "port 3000 not listening"

echo ""
echo "=============================================="
echo "SECTION 3: 文件系统关键路径对比"
echo "=============================================="
echo "--- 3a. /var/www/ 目录结构 ---"
ls -la /var/www/ 2>/dev/null || echo "/var/www/ not found"
echo "--- 3b. /var/www/site/web/ 是否存在? ---"
ls -la /var/www/site/web/ 2>/dev/null | head -20 || echo "path not found"
echo "--- 3c. bigprc_site 目录是否存在? ---"
ls -la /var/www/bigprc_site/ 2>/dev/null || echo "/var/www/bigprc_site/ not found"
echo "--- 3d. seo_env 虚拟环境是否存在? ---"
ls -la /var/www/seo_env/ 2>/dev/null || echo "/var/www/seo_env/ not found"

echo ""
echo "=============================================="
echo "SECTION 4: 流水线脚本状态"
echo "=============================================="
echo "--- 4a. /root/scripts/ 目录 ---"
ls -la /root/scripts/ 2>/dev/null || echo "/root/scripts/ not found"

echo "--- 4b. .env 文件 (脱敏: 只显示 key，隐藏 value) ---"
if [ -f /root/scripts/.env ]; then
    cat /root/scripts/.env | sed 's/=.*/=***HIDDEN***/'
else
    echo "/root/scripts/.env NOT FOUND"
fi

echo "--- 4c. database.db 是否存在? ---"
ls -lh /root/scripts/database.db 2>/dev/null || echo "database.db not found"

echo "--- 4d. pantools_export.xlsx 是否存在? ---"
ls -lh /root/scripts/pantools_export.xlsx 2>/dev/null || echo "pantools_export.xlsx not found"

echo ""
echo "=============================================="
echo "SECTION 5: Cron 定时任务"
echo "=============================================="
echo "--- 5a. root 的 crontab ---"
crontab -l 2>/dev/null || echo "no crontab for root"

echo "--- 5b. /etc/crontab ---"
cat /etc/crontab 2>/dev/null | grep -v '^#' | grep -v '^$' || echo "empty or not found"

echo "--- 5c. cron.d 目录 ---"
ls -la /etc/cron.d/ 2>/dev/null || echo "no /etc/cron.d"

echo ""
echo "=============================================="
echo "SECTION 6: OpenClaw / 控制台进程"
echo "=============================================="
echo "--- 6a. OpenClaw 进程 ---"
ps aux 2>/dev/null | grep -i 'openclaw\|claw' | grep -v grep || echo "no openclaw/claw process found"

echo "--- 6b. Node.js PM2 进程 (如果有) ---"
pm2 list 2>/dev/null || echo "pm2 not available"

echo "--- 6c. systemd 中可能相关的服务 ---"
systemctl list-units --type=service --state=running 2>/dev/null | grep -iE 'claw|open|node|api|nginx' || echo "no matching services"

echo ""
echo "=============================================="
echo "SECTION 7: SSL 证书状态"
echo "=============================================="
echo "--- 7a. Let's Encrypt 证书目录 ---"
ls -la /etc/letsencrypt/live/ 2>/dev/null || echo "no letsencrypt live dir"

echo "--- 7b. 证书有效期 ---"
for d in /etc/letsencrypt/live/*/; do
    if [ -f "$d/fullchain.pem" ]; then
        echo "--- $(basename $d) ---"
        openssl x509 -in "$d/fullchain.pem" -noout -subject -dates 2>/dev/null || echo "failed to read cert"
    fi
done

echo ""
echo "=============================================="
echo "SECTION 8: 磁盘与内存"
echo "=============================================="
echo "--- 8a. 磁盘使用 ---"
df -h / 2>/dev/null

echo "--- 8b. 内存 ---"
free -h 2>/dev/null

echo ""
echo "=============================================="
echo "=== AUDIT COMPLETE ==="
echo "请将以上全部输出复制给 Claude"
echo "=============================================="
