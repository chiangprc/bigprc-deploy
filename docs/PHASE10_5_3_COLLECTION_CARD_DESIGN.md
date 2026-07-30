# Phase 10.5-3 — Collection Card Redesign

> Role: Senior Product Designer + Design System Architect
> Status: DESIGN DOCUMENT — no code, no CSS.
> Page: https://www.bigprc.com/collection/index.html

---

## 1. Design Goal

**Current state**: The collection index feels like a "resource directory" — dense cards, small text, functional but uninspiring.

**Target state**: The collection index feels like an **editorial catalog** — each card is an invitation to explore a thoughtfully curated collection of digital resources.

> "I'm not looking at a list of links. I'm browsing a library."

---

## 2. Information Architecture

### What belongs on the card

| Element | Priority | Why |
|---------|----------|-----|
| **Collection title** | Primary | The user decides based on the topic name |
| **Theme icon** | Secondary | Visual anchor — instantly signals category |
| **Short description** | Secondary | Value proposition — "why should I click?" |
| **Resource count** | Tertiary | Social proof — "this is substantive" |
| **Featured mark** | Tertiary | Editorial signal — "our editors picked this" |

### What does NOT belong on the card

- ❌ Category tags (already grouped by theme section)
- ❌ "Explore →" link text (the entire card is the link)
- ❌ Last updated date (not meaningful for curated collections)
- ❌ Author/editor name (not relevant at this level)

---

## 3. Visual Hierarchy

```
┌─────────────────────────────────────┐
│                                     │
│  <icon>                             │  ← 20px Lucide, muted, top-left anchor
│                                     │
│  Collection Title                   │  ← 16px, semibold, dark — THE focal point
│  (max 2 lines)                      │
│                                     │
│  A short intro describing what      │  ← 14px, secondary color, 2-line clamp
│  this collection contains...        │
│                                     │
│  176 resources                      │  ← 12px, subtle accent or muted
│                                     │
└─────────────────────────────────────┘
```

### Why this order

- **Icon first**: The eye lands on the icon, instantly recognizing the theme category (nature, tools, learning). This is the fastest way to scan.
- **Title second**: After the icon, the title answers "what is this?" — the primary decision point.
- **Description third**: For undecided users, the description provides the "why."
- **Count last**: Pushed to the bottom — it's supporting information, not a decision driver.

---

## 4. Typography

| Element | Size | Weight | Color | Line Clamp |
|---------|------|--------|-------|------------|
| Theme icon | 20px | — | `var(--color-text-secondary)` | — |
| Title | 16px (`--text-subtitle`) | 600 | `var(--color-text)` | 2 lines |
| Description | 14px (`--text-body`) | 400 | `var(--color-text-secondary)` | 2 lines |
| Count | 12px (`--text-meta`) | 500 | `var(--color-accent)` | 1 line |

### Type rationale

- **16px title**: Large enough to be the focal point; small enough to fit two lines in a card. Matches `--text-subtitle`.
- **14px description**: Readable at card width (~280px). Matches `--text-body`.
- **12px count**: Supporting data, intentionally smaller. Matches `--text-meta`.
- **No bold weights**: Semibold (600) for title; regular (400) for body. Clean, restrained.

---

## 5. Spacing

```
┌─────────────────────────────────────┐
│  ← 24px →                    ← 24 →│  padding: 24px (--space-2xl)
│                                     │
│  <icon>                             │  icon at top
│  ↓ 12px                             │  gap after icon
│  Title text                         │
│  ↓ 8px                              │  gap between title and desc
│  Description                        │
│  ↓ 16px                             │  push count to bottom
│  176 resources                      │
│                                     │
└─────────────────────────────────────┘
```

| Property | Value | Token |
|----------|-------|-------|
| Card padding | 24px | `var(--space-2xl)` |
| Icon → Title gap | 12px | `var(--space-md)` |
| Title → Desc gap | 8px | `var(--space-sm)` |
| Desc → Count gap | 16px | `var(--space-lg)` |
| Card min-height | 180px | (ensures uniform height) |

### Spacing rationale

- **24px padding**: Generous breathing room. Notion uses 24px+. Linear uses 20-24px. This number says "editorial," not "data table."
- **12px after icon**: Creates a visual grouping — icon + title are perceived as one unit.
- **8px title→desc**: Tight enough to show they're related; loose enough to separate the two lines of information.
- **16px push to bottom**: Ensures the count is visually anchored at the card bottom, regardless of title/desc length. This is what makes all cards feel equal height.

---

## 6. Hover Interaction

### Default state

```
Border:     var(--border-width) solid var(--color-border)   (subtle gray)
Background: var(--color-surface)                            (warm white)
Cursor:     default
```

### Hover state

```
Border:     var(--border-width) solid var(--color-accent)   (deep blue)
Background: var(--color-bg)                                 (pure white — subtle 2% shift)
Cursor:     pointer
Title:      color → var(--color-accent)                     (signals clickability)
Icon:       color → var(--color-accent)                     (icon comes alive)
```

### Why this approach

- **No shadows**: BigPRC Design System forbids box-shadow. Good — shadows feel like "floating UI," not editorial content.
- **No transforms**: No translateY, no scale. The card doesn't "lift." It "highlights." This is restrained, confident.
- **Border + bg shift**: The 1px border changing from gray to blue is subtle but clear. The background shift from surface (#fafafa) to pure white (#fff) is almost imperceptible — just enough to feel responsive.
- **Title color change**: The most noticeable change. The blue title says "this is interactive, click me."

### Transition

```
transition: border-color var(--transition-fast),      (0.15s)
            background-color var(--transition-fast),   (0.15s)
            color var(--transition-fast);              (0.15s)
```

All three properties animate together. Fast, smooth, confident.

---

## 7. Desktop Layout

### Card Grid

```
Grid:       CSS Grid, auto-fill
Min card:   280px
Max card:   1fr (fills available space)
Gap:        16px (--space-lg)

3 columns on 960px viewport (~304px each)
2 columns on 640px viewport
```

### Theme Section

```
Max width:  960px
Margin:     0 auto 48px (--space-3xl between themes)
Header:     Icon + theme name, 18px semibold, bottom border
```

### Why 16px gap

Current 12px gap feels cramped. At 16px, cards have breathing room without feeling disconnected. This is the "Notion gallery gap" — tight enough to scan, loose enough to read.

---

## 8. Mobile Layout

```
Breakpoint: 768px
Grid:       1 column (cards stack vertically)
Padding:    16px 12px (reduced from 24px/20px)
Card pad:   20px (reduced from 24px)
Gap:        12px (reduced from 16px)
```

### Mobile considerations

- **Full-width cards**: No columns. One card per row, full viewport width minus padding.
- **Reduced padding**: 20px instead of 24px — saves ~8px per card, meaningful on 375px screens.
- **Touch target**: Entire card is tappable. The `<a>` wrapper extends to card edges.
- **Icon size**: Stays at 20px — don't shrink icons on mobile (Apple HIG principle).

---

## 9. Why This Design

### It serves the curation mission

Every design decision answers the question: "Does this make the collection feel curated?"

| Decision | Why it serves curation |
|----------|----------------------|
| Icon at top | "This was categorized by a human" |
| Title as focal point | "The topic matters more than the metadata" |
| Description clamped to 2 lines | "Enough to intrigue, not enough to replace the detail page" |
| Count at bottom | "We track quality by volume, but volume isn't the story" |
| Featured = accent border | "Our editors chose this — it's worth your time" |
| Generous padding | "This is worth spending time with" |

### It's not a navigation site

A navigation site would:
- Put the count next to the title (like a file count)
- Use compact, table-like spacing
- Show multiple metadata fields
- Use smaller text to fit more

BigPRC is not a navigation site. It's a **curation library**. The design must signal this at every level.

### Reference comparison

| Element | Stripe Docs | Linear Issues | Notion Gallery | BigPRC (proposed) |
|---------|------------|---------------|----------------|-------------------|
| Card padding | 24px | 16-20px | 24px+ | 24px |
| Title size | 16px | 14px | 16px | 16px |
| Title weight | 600 | 500 | 600 | 600 |
| Desc size | 14px | 13px | 14px | 14px |
| Gap | 16px | 12px | 16px | 16px |
| Hover | Border | BG shift | Shadow (Notion exception) | Border + BG + color |

---

## 10. Expected Improvement

### Before → After

| Metric | Before | After |
|--------|--------|-------|
| Card height consistency | Variable (no min-height) | Uniform (min-height: 180px) |
| Description readability | 12px, cramped | 14px, comfortable |
| Visual weight of title | Medium (shared with desc) | Strong (dominant element) |
| Hover signal clarity | Border-color only | Border + BG + Title color |
| Grid breathing room | 12px gap | 16px gap |
| Card → "curated collection" association | Weak (feels like a link list) | Strong (feels like an editorial catalog) |

### The feeling

**Before**: "Here are some links organized by category."

**After**: "Someone carefully selected these resources. I want to explore."

---

> **Status: DESIGN COMPLETE — awaiting confirmation to implement.**
