#!/usr/bin/env bash
# ============================================================
# bigprc.com 站点部署脚本
# 用法: bash deploy.sh
# 前提: 本脚本位于 git 仓库根目录，VPS 上已 clone 到本地
# ============================================================
set -euo pipefail

# ---------- 可调整变量 ----------
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"
SCRIPTS_DIR="/root/scripts"
TEMPLATES_DIR="/root/scripts/templates"
OPENCLAW_LOG="/root/openclaw.log"

# OpenClaw 启动命令（如与实际不同，修改此处）
# 常见形式: openclaw gateway 或 npx openclaw gateway
OPENCLAW_CMD="openclaw gateway"

echo "=============================================="
echo " BigPRC 站点部署开始"
echo " 时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

# ============================================================
# 1. 同步 Nginx 站点配置
# ============================================================
echo ""
echo "[1/5] 同步 Nginx 站点配置..."

if [ -d "$REPO_ROOT/etc/nginx/sites-available" ]; then
    cp -v "$REPO_ROOT/etc/nginx/sites-available/"* "$NGINX_AVAILABLE/"
    chown root:root "$NGINX_AVAILABLE/"*
    chmod 644 "$NGINX_AVAILABLE/"*
fi

if [ -d "$REPO_ROOT/etc/nginx/sites-enabled" ]; then
    cp -v "$REPO_ROOT/etc/nginx/sites-enabled/"* "$NGINX_ENABLED/"
    chown root:root "$NGINX_ENABLED/"*
    chmod 644 "$NGINX_ENABLED/"*
fi

# ============================================================
# 2. 同步 Nginx 全局配置（谨慎：仅当源码存在时才覆盖）
# ============================================================
echo ""
echo "[2/5] 同步 Nginx 全局配置..."

NGINX_CONF_FILES=(
    "nginx.conf"
    "mime.types"
    "fastcgi.conf"
    "fastcgi_params"
    "proxy_params"
    "scgi_params"
    "uwsgi_params"
)

for f in "${NGINX_CONF_FILES[@]}"; do
    src="$REPO_ROOT/etc/nginx/$f"
    if [ -f "$src" ]; then
        cp -v "$src" "/etc/nginx/$f"
        chown root:root "/etc/nginx/$f"
        chmod 644 "/etc/nginx/$f"
    fi
done

# ============================================================
# 3. 同步 Nginx snippet 配置（跳过自动生成的 jump_rules.conf）
# ============================================================
echo ""
echo "[3/5] 同步 Nginx snippet（跳过自动生成文件）..."

if [ -d "$REPO_ROOT/etc/nginx/snippets" ]; then
    for f in "$REPO_ROOT/etc/nginx/snippets/"*; do
        fname="$(basename "$f")"
        # jump_rules.conf 由 auto_generate.py 自动生成，不覆盖
        if [ "$fname" = "jump_rules.conf" ]; then
            echo "  ⏭ 跳过 jump_rules.conf（由 auto_generate.py 自动管理）"
            continue
        fi
        cp -v "$f" "/etc/nginx/snippets/$fname"
        chown root:root "/etc/nginx/snippets/$fname"
        chmod 644 "/etc/nginx/snippets/$fname"
    done
fi

# ============================================================
# 4. 同步 Python 脚本 & 模板
# ============================================================
echo ""
echo "[4/5] 同步 Python 脚本和模板..."

if [ -d "$REPO_ROOT/root/scripts" ]; then
    mkdir -p "$SCRIPTS_DIR" "$TEMPLATES_DIR"

    # Python 脚本
    for f in "$REPO_ROOT/root/scripts/"*.py; do
        if [ -f "$f" ]; then
            cp -v "$f" "$SCRIPTS_DIR/"
            chown root:root "$SCRIPTS_DIR/$(basename "$f")"
            chmod 755 "$SCRIPTS_DIR/$(basename "$f")"
        fi
    done

    # Jinja2 模板
    if [ -d "$REPO_ROOT/root/scripts/templates" ]; then
        for f in "$REPO_ROOT/root/scripts/templates/"*.html; do
            if [ -f "$f" ]; then
                cp -v "$f" "$TEMPLATES_DIR/"
                chown root:root "$TEMPLATES_DIR/$(basename "$f")"
                chmod 644 "$TEMPLATES_DIR/$(basename "$f")"
            fi
        done
    fi
fi

# ============================================================
# 5. 重载服务
# ============================================================
echo ""
echo "[5/5] 重载服务..."

# 5a. Nginx 语法检查 + 热重载
echo "  → 检查 Nginx 配置语法..."
if nginx -t 2>&1; then
    echo "  → 语法通过，重载 Nginx..."
    systemctl reload nginx
    echo "  ✅ Nginx 重载成功"
else
    echo "  ❌ Nginx 语法检查失败，已阻止重载！请检查配置后手动执行: systemctl reload nginx"
fi

# 5b. OpenClaw 重启（kill 旧进程 + nohup 重新启动）
echo "  → 重启 OpenClaw..."
if pkill -f "openclaw gateway" 2>/dev/null; then
    echo "  → 已终止旧 OpenClaw 进程，等待端口释放..."
    sleep 2
else
    echo "  → 未发现运行中的 OpenClaw 进程，直接启动..."
fi

# 确保 nvm 可用（OpenClaw 依赖 Node.js）
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    source "$NVM_DIR/nvm.sh"
fi

nohup $OPENCLAW_CMD > "$OPENCLAW_LOG" 2>&1 &
echo "  ✅ OpenClaw 已通过 nohup 后台启动 (PID: $!)"

# 5c. Python 脚本提示（由 crontab 定时触发，无需手动执行）
echo "  ℹ️  Python 脚本已同步。Crontab 将在预定时间自动触发 auto_generate.py。"

echo ""
echo "=============================================="
echo " 部署完成"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="
echo ""
echo "后续可手动验证:"
echo "  curl -I https://www.bigprc.com       # 主站"
echo "  curl -I https://claw.bigprc.com      # OpenClaw"
echo "  tail -f /root/openclaw.log           # OpenClaw 日志"
echo "  /root/scripts/seo_env/bin/python3 /root/scripts/auto_generate.py  # 手动触发全量生成"
