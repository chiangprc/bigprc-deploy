#!/usr/bin/env bash
# ============================================================
# bigprc.com 站点部署脚本 (Git 局部管理 · 软链接方式)
# 用法: bash deploy.sh
# 前提: VPS 上已 git clone 到 /root/bigprc-deploy
#
# 安全原则:
#   - 只用 git pull 更新代码，绝不 cp/rsync 覆盖系统目录
#   - Nginx 配置通过 ln -sf 软链接生效，源文件留在仓库内
#   - 手工静态页面通过 ln -sf 软链接到 /var/www/site/web/
# ============================================================
set -euo pipefail

# ---------- 可调整变量 ----------
DEPLOY_ROOT="${DEPLOY_ROOT:-/root/bigprc-deploy}"
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"
NGINX_SNIPPETS="/etc/nginx/snippets"
SCRIPTS_DIR="/root/scripts"
TEMPLATES_DIR="/root/scripts/templates"
OPENCLAW_LOG="/root/openclaw.log"
OPENCLAW_CMD="openclaw gateway"
SITE_WEB="/var/www/site/web"

echo "=============================================="
echo " BigPRC 站点部署开始 (Git + 软链接)"
echo " 时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

# ============================================================
# 1. Git 拉取最新代码
# ============================================================
echo ""
echo "[1/6] git pull 拉取最新代码..."

cd "$DEPLOY_ROOT"
git pull origin main

echo "  ✅ 仓库已更新到 $(git rev-parse --short HEAD)"

# ============================================================
# 2. Nginx 站点配置 → 软链接到 sites-enabled
# ============================================================
echo ""
echo "[2/6] 部署 Nginx 站点配置（ln -sf）..."

if [ -d "$DEPLOY_ROOT/etc/nginx/sites-available" ]; then
    for f in "$DEPLOY_ROOT/etc/nginx/sites-available/"*; do
        [ -f "$f" ] || continue
        fname="$(basename "$f")"
        ln -sf "$f" "$NGINX_AVAILABLE/$fname"
        ln -sf "$f" "$NGINX_ENABLED/$fname"
        echo "  → $fname"
    done
fi

# ============================================================
# 3. Nginx snippets（跳过自动生成的 jump_rules.conf）
# ============================================================
echo ""
echo "[3/6] 部署 Nginx snippet（跳过自动生成文件）..."

if [ -d "$DEPLOY_ROOT/etc/nginx/snippets" ]; then
    mkdir -p "$NGINX_SNIPPETS"
    for f in "$DEPLOY_ROOT/etc/nginx/snippets/"*; do
        [ -f "$f" ] || continue
        fname="$(basename "$f")"
        if [ "$fname" = "jump_rules.conf" ]; then
            echo "  ⏭ 跳过 jump_rules.conf（由 auto_generate.py 自动管理）"
            continue
        fi
        ln -sf "$f" "$NGINX_SNIPPETS/$fname"
        echo "  → $fname"
    done
fi

# ============================================================
# 4. Python 脚本 & 模板 → 软链接
# ============================================================
echo ""
echo "[4/6] 部署 Python 脚本和模板（ln -sf）..."

if [ -d "$DEPLOY_ROOT/root/scripts" ]; then
    mkdir -p "$SCRIPTS_DIR" "$TEMPLATES_DIR"

    for f in "$DEPLOY_ROOT/root/scripts/"*.py; do
        [ -f "$f" ] || continue
        ln -sf "$f" "$SCRIPTS_DIR/$(basename "$f")"
        echo "  → $(basename "$f")"
    done

    if [ -d "$DEPLOY_ROOT/root/scripts/templates" ]; then
        for f in "$DEPLOY_ROOT/root/scripts/templates/"*.html; do
            [ -f "$f" ] || continue
            ln -sf "$f" "$TEMPLATES_DIR/$(basename "$f")"
            echo "  → templates/$(basename "$f")"
        done
    fi
fi

# ============================================================
# 5. 手工静态页面 → 软链接到 /var/www/site/web/
# ============================================================
echo ""
echo "[5/6] 部署手工静态页面（ln -sf）..."

if [ -d "$DEPLOY_ROOT/root/custom-pages" ]; then
    mkdir -p "$SITE_WEB"
    while IFS= read -r -d '' f; do
        rel="${f#$DEPLOY_ROOT/root/custom-pages/}"
        target="$SITE_WEB/$rel"
        mkdir -p "$(dirname "$target")"
        ln -sf "$f" "$target"
        echo "  → $rel"
    done < <(find "$DEPLOY_ROOT/root/custom-pages" -type f -print0)
fi

# ============================================================
# 6. 重载服务
# ============================================================
echo ""
echo "[6/6] 重载服务..."

# 5a. Nginx 语法检查 + 热重载
echo "  → 检查 Nginx 配置语法..."
if nginx -t 2>&1; then
    echo "  → 语法通过，重载 Nginx..."
    systemctl reload nginx
    echo "  ✅ Nginx 重载成功"
else
    echo "  ❌ Nginx 语法检查失败，已阻止重载！请检查配置后手动执行: systemctl reload nginx"
    exit 1
fi

# 5b. OpenClaw 重启
echo "  → 重启 OpenClaw..."
if pkill -f "openclaw gateway" 2>/dev/null; then
    echo "  → 已终止旧进程，等待端口释放..."
    sleep 2
else
    echo "  → 未发现运行中的进程，直接启动..."
fi

export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    source "$NVM_DIR/nvm.sh"
fi

nohup $OPENCLAW_CMD > "$OPENCLAW_LOG" 2>&1 &
echo "  ✅ OpenClaw 已启动 (PID: $!)"

echo ""
echo "=============================================="
echo " 部署完成 — $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="
echo ""
echo "后续可手动验证:"
echo "  curl -I https://www.bigprc.com       # 主站"
echo "  curl -I https://claw.bigprc.com      # OpenClaw"
echo "  tail -f /root/openclaw.log           # OpenClaw 日志"
