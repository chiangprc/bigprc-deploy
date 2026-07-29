/* ============================================================
   BigPRC Icon System v1.0
   Phase 10.4B-2 — Icon System Foundation

   Usage:
     1. Include Lucide CDN before this script:
        <script src="https://unpkg.com/lucide@latest"></script>

     2. Use semantic names to render Lucide icons:
        BPRC.icon('edit')       → <i data-lucide="pencil-line" class="icon-sm icon-muted"></i>
        BPRC.icon('success')    → <i data-lucide="circle-check" class="icon-sm icon-success"></i>

     3. Size / color via CSS classes (defined in _tokens.css):
        .icon-sm   .icon-md
        .icon-success .icon-warning .icon-danger .icon-info .icon-neutral .icon-accent .icon-muted

     4. Icon + text label:
        <span class="icon-label">
          <i data-lucide="pencil-line" class="icon-sm icon-muted"></i>
          编辑视角
        </span>
   ============================================================ */

window.BPRC = window.BPRC || {};

/* ── Semantic Name → Lucide Icon Name ──────────────────────── */
BPRC.ICONS = {

    /* Section / Navigation */
    edit:               'pencil-line',
    featured:           'sparkles',
    resource:           'list',
    link:               'link',
    faq:                'message-circle',
    collection:         'library',
    dashboard:          'layout-dashboard',
    editorial:          'edit',
    site:               'globe',
    search:             'search',

    /* Status / Semantic */
    success:            'circle-check',
    warning:            'alert-circle',
    danger:             'circle-x',
    empty:              'circle',
    info:               'info',
    complete:           'check-circle-2',
    error:              'x-circle',
    featured_star:      'star',
    alert:              'alert-triangle',
    new_item:           'plus-circle',
    merge:              'git-merge',

    /* Action */
    optimize:           'wrench',
    cli:                'terminal',

    /* Meta */
    audience:           'users',

    /* Interaction */
    expand:             'chevron-down',
    collapse:           'chevron-up'
};

/* ── Emoji → Semantic Name (for automated migration) ───────── */
BPRC.EMOJI_MAP = {
    '📝': 'edit',
    '🌟': 'featured',
    '📋': 'resource',
    '🔗': 'link',
    '💬': 'faq',
    '📚': 'collection',
    '📊': 'dashboard',
    '✍️': 'editorial',
    '🌐': 'site',
    '🔍': 'search',
    '🟢': 'success',
    '🟡': 'warning',
    '🔴': 'danger',
    '⚪': 'empty',
    '🔵': 'info',
    '✅': 'complete',
    '❌': 'error',
    '⭐': 'featured_star',
    '⚠️': 'alert',
    '🆕': 'new_item',
    '🔀': 'merge',
    '🔧': 'optimize',
    '💡': 'cli',
    '👥': 'audience',
    '▶':  'expand',
    '▼':  'collapse'
};

/* ── Render helper ─────────────────────────────────────────── */
BPRC.icon = function(semanticName, opts) {
    opts = opts || {};
    var lucideName = BPRC.ICONS[semanticName] || semanticName;
    var size  = opts.size  || 'sm';
    var color = opts.color || 'muted';
    return '<i data-lucide="' + lucideName + '" class="icon-' + size + ' icon-' + color + '"></i>';
};

/* ── Emoji → Icon HTML (for migration tooling) ─────────────── */
BPRC.emojiToIcon = function(emoji, opts) {
    var semantic = BPRC.EMOJI_MAP[emoji];
    return semantic ? BPRC.icon(semantic, opts) : emoji;
};

/* ── Icon label (icon + text) ───────────────────────────────── */
BPRC.iconLabel = function(semanticName, text, opts) {
    return '<span class="icon-label">' + BPRC.icon(semanticName, opts) + ' ' + text + '</span>';
};
