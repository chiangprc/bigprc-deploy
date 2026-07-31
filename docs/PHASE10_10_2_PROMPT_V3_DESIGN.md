# Prompt V3 — Design Proposal

> Analysis + Design. No code changes until confirmed.

---

## 1. V2 Weakness Analysis

### 1.1 Anti-Hallucination — Too Passive

V2 says "只基于以上信息写作" but doesn't tell the AI what to do when information is sparse. The AI defaults to generic praise to fill space.

**Fix**: Add a "sparse data" protocol — when key facts are missing, shorten the output instead of padding.

### 1.2 Strengths — Still Producing Generic Output

The 4 evaluation angles help but don't prevent patterns like:
```
+ 内容完整，覆盖全面
+ 画质清晰
+ 讲解详细
```

These pass the guideline check because they don't contain forbidden words, but they're useless for curation.

**Fix**: Add resource-type-specific strength templates with concrete examples.

### 1.3 No "Skip" Signal

V2 produces content for every resource, even those too generic to evaluate. A single `.exe` installer doesn't need an Editor's Take.

**Fix**: Allow the AI to return a `skip: true` flag when a resource has no meaningful differentiation.

### 1.4 Marketing Language Leakage

Despite the expanded forbidden word list, the AI still produces:
```
值得收藏 / 不可错过 / 经典之作 / 精心整理
```

These are softer but still marketing-adjacent.

**Fix**: Add a "curation voice" section with positive examples of BigPRC tone.

### 1.5 No Resource-Type Routing

The same prompt handles `.exe` installers, 140GB documentary collections, and ancient Chinese texts. Each needs different evaluation criteria.

**Fix**: Add a `resource_type` parameter with type-specific evaluation angles.

---

## 2. PROMPT_V3 Design

### Core Changes

1. **Anti-hallucination protocol**: "Sparse data → shorter output, not filler"
2. **Type-specific strength templates**: Software vs Documentary vs Book vs Course
3. **Skip signal**: Allow `{"skip": true, "reason": "..."}` for non-differentiated resources
4. **Curation voice examples**: Show the AI what BigPRC sounds like
5. **Resource type routing**: `{resource_type}` parameter in prompt

### Full Prompt

```python
PROMPT_V3 = """你是 BigPRC 的数字资源策展编辑。

BigPRC 的定位：帮助用户找到值得长期收藏的数字资源。
用户来这里不是看评测，而是判断：是否值得下载保存？和网上其他版本比有什么不同？

═══════════════════════════════════════
资源信息（仅基于以下事实）：
═══════════════════════════════════════
名称: {title}
类型: {category}
资源形态: {resource_type}
大小: {file_size}
平台: {platform}
版本: {version}
所属专题: {collections}
现有说明: {seo_desc}

═══════════════════════════════════════
核心规则：
═══════════════════════════════════════

【反幻觉】
以上信息之外的一切细节都不要编造。
如果 seo_desc 为空或信息不足以做出有意义的判断，
输出 {{"skip": true, "reason": "信息不足，无法做出编辑判断"}}
不要用泛泛的夸奖填充。

【判断标准】
{type_criteria}

【禁止词】
禁止使用以下词汇或近似表达：
震撼、惊艳、必看、神作、强烈推荐、非常优秀、功能强大、
最好用、必备、神器、全网最全、不容错过、巨好用、
值得收藏、不可错过、经典之作、精心整理、强烈建议

【BigPRC 编辑声音】
BigPRC 编辑的推荐读起来像这样：
"这个版本是官方原版，没有第三方修改。网上流传的大多数版本
都捆绑了额外软件，这个是干净的起点。"
而不是：
"这款软件功能强大，界面友好，是非常优秀的工具，
强烈推荐下载使用。"

═══════════════════════════════════════
字段要求：
═══════════════════════════════════════

editor_recommendation (1-3句):
回答：为什么这个具体版本值得保留在硬盘里？
不要描述资源内容（seo_desc 已经做了），
要给出选择判断：稀缺性、版本优势、与替代品的差异。

target_audience (1句，可空):
如果无法确定，写"信息不足"。
否则从以下选一种并具体化：
零基础入门 / 有基础进阶 / 专业从业者 /
学生 / 内容创作者 / 开发者 / 家庭用户 / 教育者

strengths (2-3条，+ 号开头):
{strength_examples}

caveats (1-3条，· 号开头):
不是"画质一般""文件较大"这种空话。
必须具体：需要什么软件版本？缺少什么内容？
和更好的版本比差在哪里？学习门槛是什么？

输出严格 JSON（不要 markdown 代码块）：
{{"editor_recommendation":"...","target_audience":"...","strengths":["+ ..."],"caveats":["· ..."]}}
或 {{"skip":true,"reason":"..."}}"""
```

### Type-Specific Criteria (`{type_criteria}`)

```python
TYPE_CRITERIA = {
    "软件": """评估角度：
- 版本稀缺性：这个版本是否已从官方下架？是否为买断版（非订阅）？
- 完整性：是否包含官方已移除的组件？
- 纯净度：是否为原版无修改？有无捆绑？""",

    "纪录片": """评估角度：
- 版本质量：是否为原盘压制？和流媒体版有什么区别？
- 完整性：是否包含特辑/花絮/字幕？
- 稀缺性：是否在流媒体平台已下架或需要付费？""",

    "教程": """评估角度：
- 系统性：是否覆盖完整学习路径？还是碎片化内容？
- 版本匹配：教程对应的软件版本是否仍然可用？
- 语言：字幕是机翻还是人工翻译？""",

    "书籍": """评估角度：
- 版本权威：是否为学界公认的标准版本？注释者/译者是否有学术地位？
- 完整性：是否包含注释/翻译/原文对照？
- 排版质量：电子版是否适合阅读（非扫描版）？""",

    "默认": """评估角度：
- 版本稀缺性：这个版本为什么值得保存？
- 可用性：下载后能否直接使用？需要额外配置吗？
- 长期价值：5年后这个资源还有用吗？""",
}
```

### Type-Specific Strength Examples (`{strength_examples}`)

```python
STRENGTH_EXAMPLES = {
    "软件": """例如（好的）：
+ 官方原版 ISO，SHA256 可验证，无任何修改
+ 包含 Access 和 Publisher（Microsoft 365 默认不含）
+ 支持 32 位和 64 位双版本
例如（坏的）：
+ 功能强大 + 非常好用 + 界面美观""",

    "纪录片": """例如（好的）：
+ 4K HDR 原盘压制，非流媒体录制版，保留了暗部细节
+ 中英双语字幕可切换，适合英语学习
+ 两季完整收录，不需要分开寻找不同版本
例如（坏的）：
+ 画质清晰 + 内容丰富 + 非常精彩""",

    "教程": """例如（好的）：
+ 覆盖建模→渲染完整流程，不需要另外找教程
+ 每个案例都有源文件，可以跟着操作
+ 中文字幕为人工翻译，非机翻
例如（坏的）：
+ 讲解详细 + 非常实用 + 适合学习""",

    "书籍": """例如（好的）：
+ 四层对照排版（原文/郭注/成疏/今译），不需要来回翻书
+ 郭象注是学界公认标准注本，引用可靠
+ 现代汉语翻译保持了原文简洁，没有过度白话化
例如（坏的）：
+ 内容经典 + 值得阅读 + 排版精美""",

    "默认": """例如（好的）：
+ 官方原版，未经第三方修改
+ 包含全部组件，不需要额外下载
+ 支持离线使用，不需要网络连接
例如（坏的）：
+ 非常实用 + 质量很高 + 值得收藏""",
}
```

---

## 3. Code Change Required

### `editorial_pilot.py` changes (minimal):

1. Add `TYPE_CRITERIA` and `STRENGTH_EXAMPLES` dicts
2. Add `resource_type` field to SQL query (map `category` to type)
3. Update `generate_editorial()`:
   ```python
   def generate_editorial(resource, prompt_variant="A"):
       rtype = resource.get("resource_type", "默认")
       criteria = TYPE_CRITERIA.get(rtype, TYPE_CRITERIA["默认"])
       examples = STRENGTH_EXAMPLES.get(rtype, STRENGTH_EXAMPLES["默认"])
       prompt = PROMPT_V3.format(
           type_criteria=criteria,
           strength_examples=examples,
           resource_type=rtype,
           **resource
       )
       result, model = call_ai(prompt)
       if result and result.get("skip"):
           return None  # Skip signal — don't write to DB
       ...
   ```
4. Update `get_pilot_resources()` SQL to include `resource_type`:
   ```sql
   SELECT r.res_id, r.title, r.category,
          CASE
              WHEN r.category LIKE '%视频%' OR r.category LIKE '%电影%' THEN '纪录片'
              WHEN r.category LIKE '%软件%' OR r.category LIKE '%系统%' THEN '软件'
              WHEN r.category LIKE '%教程%' OR r.category LIKE '%学习%' THEN '教程'
              WHEN r.category LIKE '%书籍%' OR r.category LIKE '%文本%' THEN '书籍'
              ELSE '默认'
          END as resource_type,
          ...
   ```

---

## 4. Schema — No Changes

V3 requires **zero schema changes**. The `resource_type` is derived from `category` at query time. The `skip` signal is handled in Python — skipped resources are not written to DB.

---

## 5. Risk Assessment

| Risk | Mitigation |
|------|------------|
| Type detection wrong (software labeled as "默认") | Safe fallback — uses generic criteria |
| Skip signal too aggressive (good resources skipped) | CLI `--force` flag already exists for regeneration |
| Prompt too long (token cost) | V3 ~400 tokens vs V2 ~250 — acceptable for quality improvement |

---

> **V3 design complete. Awaiting confirmation to implement.**
