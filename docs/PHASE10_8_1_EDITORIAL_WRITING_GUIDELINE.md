# BigPRC Editorial Writing Guideline v1.0

> For: Editor's Take, 推荐理由, Caveats, Target Audience
> Principle: Every sentence must help the user decide.

---

## 1. Editor's Take — 写作原则

### The Rule

> If you can copy-paste this recommendation onto another resource, it's not specific enough.

### ✅ DO

```
"这是目前中文互联网上最完整的 Blender 教程合集。
从基础建模到动画渲染，覆盖了 3.0 到 4.0 版本的全部核心功能。
适合从零开始的初学者 —— 前 10 集专门针对完全没接触过 3D 软件的用户。"
```

**Why it works**: Specific version range, specific audience, specific content scope.

### ❌ DON'T

```
"Blender 是一款功能强大的 3D 建模软件，本教程合集非常优秀，
值得学习和收藏。适合所有对 3D 感兴趣的用户。"
```

**Why it fails**: Generic praise, no specifics, "所有人" audience.

### The Litmus Test

After writing, ask:

| Question | Must Answer |
|----------|------------|
| What exactly is in this resource? | Yes — specific content, version, scope |
| Why is THIS version the one to get? | Yes — compared to alternatives |
| Who will actually benefit from this? | Yes — specific audience, not "everyone" |
| What does the user need to know first? | Optional — prerequisites, caveats |

If any answer is vague, rewrite.

---

## 2. 推荐理由模板

### Structure

```
适合：[具体用户画像]

为什么推荐：[编辑判断, 1-2 句]

它解决的问题：[用户痛点]

相比其他选择：[差异化]

需要注意：[使用门槛或限制]
```

### Example — Good

```
适合：需要用 DaVinci Resolve 进行专业调色的视频创作者。

为什么推荐：这是目前少数完整覆盖 Fusion 和 Fairlight
两个模块的中文教程。市面大部分教程只讲剪辑和调色。

它解决的问题：Resolve 的 Fusion 节点式合成和 Fairlight
音频后期对有剪辑基础的用户来说门槛很高，这套教程
从节点逻辑讲起，不需要 AE 或 Audition 基础。

相比其他选择：比 YouTube 免费教程系统，比官方文档更中文友好，
比国内付费课程便宜 90%。

需要注意：需要 Resolve 17 或更高版本。前 3 集关于
软件安装的内容已过期，建议直接从第 4 集开始。
```

### Example — Too Generic (DO NOT USE)

```
适合：所有人。

为什么推荐：资源质量高，内容丰富，非常实用。

它解决的问题：帮助用户学习。

相比其他选择：更好更全面。

需要注意：无。
```

---

## 3. Caveats — 写作规范

### Principle

> Caveats build trust. A resource with no caveats reads as either untested or dishonest.

### Required Categories

| Category | Example |
|----------|---------|
| **学习成本** | "需要 Python 基础" / "前 2 小时是环境配置" / "英文原版，无中文字幕" |
| **使用限制** | "仅支持 Windows" / "需要 16GB 以上内存" / "夸克网盘，需要客户端" |
| **适用边界** | "不适合完全零基础" / "不涵盖 2024 年后的新版功能" / "偏理论，实操较少" |
| **不适合人群** | "如果你只需要基本剪辑，Premiere 自带教程更合适" |

### Caveats Tone

- Be factual, not apologetic. "需要 Python 基础" not "遗憾的是需要 Python 基础。"
- Be specific. "仅支持 Windows" not "部分系统可能不兼容。"
- Be helpful. Always suggest an alternative when saying "不适合 XX 人群。"

---

## 4. Target Audience — 标准

### The Rule

> "所有人" is never the right answer.

### Audience Taxonomy

| Label | Description | Example Match |
|-------|------------|---------------|
| 零基础入门 | 从未接触过该领域 | "从零学 Python" 课程 |
| 有基础进阶 | 了解基础，需要深入 | Blender 高级材质教程 |
| 专业从业者 | 日常工作使用 | DaVinci Resolve 专业调色 |
| 学生 | 在校学习需要 | 大学物理实验模拟软件 |
| 内容创作者 | 制作内容发布 | 视频剪辑素材包 |
| 开发者 | 编程/技术背景 | Linux 发行版镜像集合 |
| 家庭用户 | 亲子/家庭场景 | BBC 纪录片合集 |
| 教育者 | 教学/培训场景 | 地理课件素材库 |

### Multi-Audience

A resource CAN target multiple audiences. Example:

```
适合：
· 正在准备英语四级考试的大学生
· 需要提升听力能力的中级英语学习者
```

But each audience must be specific. No "英语学习者" — too broad.

---

## 5. SEO vs Editor's Take — 职责分离

### The Problem

AI-generated SEO descriptions and editorial recommendations both describe the resource. If they say the same thing, the editorial layer adds no value.

### The Distinction

| | SEO Description | Editor's Take |
|---|----------------|---------------|
| **Purpose** | Help search engines understand the content | Help humans decide to download |
| **Audience** | Googlebot | Real user on the page |
| **Style** | Factual, comprehensive, keyword-rich | Judgmental, comparative, concise |
| **Length** | 80-200 words | 30-80 words |
| **Contains** | What the resource IS | Why we CHOSE it |
| **Tone** | Neutral, informative | Opinionated, editorial |

### Example — Same Resource, Different Content

**SEO Description**:
```
DaVinci Resolve 是由 Blackmagic Design 开发的免费专业视频编辑软件，
支持剪辑、调色、音频后期和视觉特效。
本教程合集包含从入门到高级的完整课程体系，
共 42 集，涵盖 Fusion 节点合成、Fairlight 音频处理等模块。
总时长约 38 小时，中文字幕。
```

**Editor's Take**:
```
少数中文教程真正讲透 Fusion 和 Fairlight 的合集。
大部分 Resolve 教程只教剪辑和调色，
这套从节点逻辑讲起，填补了中文教程的一个空白。
适合已经从 Premiere 转到 Resolve、
需要进阶的创作者。
```

### The Test

> If you delete the SEO description, does the page still help the user decide? YES → Editor's Take is working.
> If you delete the Editor's Take, does Google still understand the page? YES → SEO description is working.

---

## 6. Quality Checklist

Before publishing any Editor's Take, verify:

```
[ ] 包含至少一个具体的版本号、时间范围或内容范围
[ ] 包含至少一个使用场景或用户画像
[ ] 包含至少一个"与其他选择相比"的比较点
[ ] 不使用 "非常" / "强大" / "优秀" / "推荐" 作为独立评价
[ ] Caveats 不为空（每个资源都有边界条件）
[ ] Target audience 不是 "所有人"
[ ] SEO description 和 Editor's Take 不重复相同信息
[ ] 可以在 15 秒内读完 Editor's Take
[ ] 读完 Editor's Take 后, 用户能判断 "适不适合我"
```

---

## 7. AI Generation Guidelines

When using AI to draft Editor's Take content:

### Prompt Template

```
你是一位数字资源策展编辑。

请为以下资源撰写 Editor's Take：

资源名称：
资源类型：（软件/教程/素材/书籍/纪录片/...）
文件大小：
核心内容：

要求：
1. 1-2 句话说明为什么推荐这个资源，必须包含具体理由
2. 列出 1-2 个适合的用户人群（不要写"所有人"）
3. 列出 2-3 个推荐理由（+ 号开头）
4. 列出 1-2 个注意事项（如果适用）
5. 不使用"非常优秀""功能强大""值得推荐"等泛泛评价

格式：
适合：
为什么推荐：
推荐理由：
+ 
+ 
+ 
注意事项：
· 
· 
```

### Human Review Required

AI-generated content MUST be reviewed for:
- [ ] Accuracy: version numbers, content scope are correct
- [ ] Tone: reads as human editorial voice, not AI template
- [ ] Specificity: contains concrete details, not generic praise
- [ ] Caveats: honest about limitations

---

> **Guideline v1.0 frozen. All future Editor's Take content must pass the Quality Checklist.**
