/* ============================================================
   BigPRC Icon System v1.0
   Emoji → Lucide icon mapping. Reference only — NOT loaded
   at runtime. Used during Phase 10.4B-2 migration to guide
   manual emoji-to-icon replacement.

   Lucide CDN:
     <script src="https://unpkg.com/lucide@latest"></script>
     <i data-lucide="icon-name"></i>

   Icon sizing:
     Default: 16px   data-lucide="icon-name"
     Medium:  20px   data-lucide="icon-name" style="width:20px;height:20px"

   Icon color:
     Inherits from parent text color.
     Use CSS: .icon-success { color: var(--color-success); }
             .icon-warning { color: var(--color-warning); }
             .icon-danger  { color: var(--color-danger); }
             .icon-info    { color: var(--color-info); }
             .icon-muted   { color: var(--color-text-secondary); }

   Icon + text spacing:
     gap: 6px (inline-flex + align-items:center)

   DO NOT use icon for:
     - Pure data values in tables
     - Text-only category/tag labels
     - Inline paragraph text
   ============================================================ */

const BigPRC_ICON_MAP = {

    /* ── Section / Navigation ─────────────────────────────── */
    '📝': 'pencil-line',       // 编辑视角, content edit
    '🌟': 'sparkles',          // 编辑精选
    '📋': 'list',              // 资源列表, Discovery Review
    '🔗': 'link',              // 探索更多专题
    '💬': 'message-circle',    // 常见问题
    '📚': 'library',           // 专题管理, 专题索引
    '📊': 'layout-dashboard',  // 工作台, 编辑工作台
    '✍️': 'edit',              // 编辑工作台 (alternate)
    '🌐': 'globe',             // 前台页面
    '🔍': 'search',            // 搜索

    /* ── Status / Semantic ────────────────────────────────── */
    '🟢': 'circle-check',      // 稳定, 已完成, 通过
    '🟡': 'alert-circle',      // 警告, 部分完成, 待处理
    '🔴': 'circle-x',          // 危险, 错误, 退回
    '⚪': 'circle',             // 无数据, 未生成
    '🔵': 'info',              // 信息, 待审核
    '✅': 'check-circle-2',    // 已发布, 已覆盖, all clear
    '❌': 'x-circle',          // 加载失败, 错误
    '⭐': 'star',              // Featured
    '⚠️': 'alert-triangle',    // 规则异常, 警告
    '🆕': 'plus-circle',       // 新候选
    '🔀': 'git-merge',         // 重叠, Merge

    /* ── Action ───────────────────────────────────────────── */
    '🔧': 'wrench',            // 优化规则
    '💡': 'terminal',          // CLI 提示

    /* ── Meta ──────────────────────────────────────────────── */
    '👥': 'users',             // 适合人群

    /* ── Interaction ──────────────────────────────────────── */
    '▶':  'chevron-down',      // 展开 (arrow used in both directions in UI)
    '▼':  'chevron-up',        // 收起
};

/* ── Icon color classes ──────────────────────────────────── */
/*
   .icon-success  { color: var(--color-success); }
   .icon-warning  { color: var(--color-warning); }
   .icon-danger   { color: var(--color-danger); }
   .icon-info     { color: var(--color-info); }
   .icon-neutral  { color: var(--color-neutral); }
   .icon-accent   { color: var(--color-accent); }
   .icon-muted    { color: var(--color-text-secondary); }
*/

/* ── Usage example (after Lucide CDN loaded) ─────────────── */
/*
   Before: <span>📝 编辑视角</span>
   After:  <span style="display:inline-flex;align-items:center;gap:6px">
             <i data-lucide="pencil-line" class="icon-muted"></i>
             编辑视角
           </span>
*/
