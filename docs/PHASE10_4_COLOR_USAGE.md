# BigPRC Color Usage Rules

> Phase 10.4B-1 — Color Map → Token Migration
>
> 本文档定义 BigPRC 项目的颜色使用规则。所有颜色选择必须符合本文档。

---

## 1. 允许使用硬编码 hex 的场景

| 场景 | 示例 | 理由 |
|------|------|------|
| Token 定义文件 | `_tokens.css: --color-success: #1a6b4f` | 唯一事实来源 |
| 浏览器 UI 元素 | `::-webkit-scrollbar-thumb { background: #ccc }` | 跨平台兼容 |
| 打印样式 | `@media print { color: #000 }` | 独立上下文 |
| 白/黑色通用值 | `color: #fff` (on dark bg)`color: #000` (print) | 不需要 Token |
| 第三方组件覆盖 | 极少场景，需要注释说明 | 例外 |

## 2. 禁止使用硬编码 hex 的场景

| 场景 | 违规示例 | 正确做法 |
|------|---------|----------|
| 业务页面 CSS | `.error{color:#c0392b}` | `color:var(--color-danger)` |
| JS 生成的内联样式 | `style="color:#1a6b4f"` | `style="color:var(--color-success)"` |
| JS 颜色映射函数 | `return '#f0a030'` | `return {c:'var(--color-warning)'}` |
| 状态指示色 | `background:#e8f5e9` | `background:var(--color-success-soft)` |

## 3. Semantic Color Map

```
success   — 成功 / 稳定 / 完成 / CORE
warning   — 警告 / 待处理 / 部分完成 / NICHE
danger    — 错误 / 失败 / 异常 / THIN / unstable / broken
info      — 信息 / 新发现 / SOLID / blue
neutral   — 无数据 / 空状态 / 未知 / EMPTY
accent    — 品牌强调 / Interactive / Featured
```

## 4. JS Color Pattern (Approved)

```javascript
// ✅ CORRECT — return semantic keys, CSS handles color
function getColor(status) {
  var map = {
    'good': { c: 'var(--color-success)', bg: 'var(--color-success-soft)' },
    'warn': { c: 'var(--color-warning)', bg: 'var(--color-warning-soft)' },
    'bad':  { c: 'var(--color-danger)',  bg: 'var(--color-danger-soft)'  }
  };
  return map[status] || { c: 'var(--color-neutral)', bg: 'var(--color-neutral-soft)' };
}

// Usage: style="background:'+getColor(s).bg+';color:'+getColor(s).c+'"
```

```javascript
// ❌ WRONG — hardcoded hex in JS
function getColor(status) {
  if (status === 'good') return '#1a6b4f';
  if (status === 'warn') return '#f0a030';
  return '#999';
}
```

## 5. CSS Pattern (Approved)

```css
/* ✅ CORRECT */
.error   { color: var(--color-danger); }
.success { color: var(--color-success); }
.warning { color: var(--color-warning); }
```

```css
/* ❌ WRONG */
.error   { color: #c0392b; }
.success { color: #1a6b4f; }
```

## 6. Enforcement

- CI 检查：`grep -Pn '#[0-9a-fA-F]{6}' root/ --include="*.html" | grep -v _tokens | grep -v design-tokens`
- Code Review：JS 中 `color:` + hex = BLOCK
- Phase 10.4B-1 之后新增代码必须遵循本规则

---

> **Version**: v1.0
> **Status**: FROZEN
> **Applies to**: All HTML/CSS/JS files in `root/`
