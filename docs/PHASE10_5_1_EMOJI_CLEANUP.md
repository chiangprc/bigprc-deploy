# Phase 10.5-1 — Python Emoji Source Cleanup

## Modified Files

| File | Change |
|------|--------|
| `auto_generate.py` | `COLLECTION_THEMES`: emoji→icon name; theme dict gets `icon` field |
| `collection_gap.py` | `action_label`: emoji prefix removed from 4 labels |
| `collection_index.html` | `<h2>` renders `<i data-lucide>` before theme name |
| `layout.html` | Added `DOMContentLoaded` → `lucide.createIcons()` for static pages |
| `editorial-detail.html` | `📄` → `<i data-lucide="file-text">` |

## Emoji Mapping Table

| Before | After (text) | Lucide Icon |
|--------|-------------|-------------|
| 🌍 自然探索 | 自然探索 | `globe` |
| 📚 人文经典 | 人文经典 | `library` |
| 🛠 效率工具 | 效率工具 | `wrench` |
| 🎓 学习成长 | 学习成长 | `graduation-cap` |
| 🔍 其他探索 | 其他探索 | `compass` |
| ✅ 已全覆盖 | 已全覆盖 | (rendered by actionClass JS) |
| 🔧 建议完善规则 | 建议完善规则 | (rendered by actionClass JS) |
| 🔀 多个专题重叠 | 多个专题重叠 | (rendered by actionClass JS) |
| 🆕 新专题候选 | 新专题候选 | (rendered by actionClass JS) |
| 📄 (error) | — | `file-text` |

## Before / After

| Metric | Before | After |
|--------|--------|-------|
| HTML emoji in scope | 1 (📄) | 0 |
| Python emoji in web output | 9 (theme names + labels) | 0 |
| Lucide init on static pages | missing | DOMContentLoaded |

## Re-run Required

After deploy, run:
```bash
python3 auto_generate.py
```
This regenerates `collection/index.html` with Lucide icons replacing theme emoji.
