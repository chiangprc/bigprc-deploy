# Phase 10.10.2 — AI Editorial Prompt Optimization

---

## A. Current Prompt Problems

| # | Problem | Example of Bad Output | Root Cause |
|---|---------|----------------------|------------|
| 1 | **AI hallucination** — fabricates content from title | "采用8K IMAX胶片拍摄" (实际是HDTV录制) | Prompt doesn't instruct AI to distinguish known facts from guesses |
| 2 | **Generic praise** — no curation judgment | "内容精彩，值得收藏" (这可以用在任何资源上) | Strengths format doesn't teach curation-specific evaluation |
| 3 | **Shallow caveats** — unhelpful | "画质较低" / "需要中文字幕" | Caveats prompt is too vague — needs curation-specific categories |
| 4 | **Missing scarcity signal** — no "why this version" | "BBC纪录片合集，内容丰富" | Prompt focuses on description, not differentiation |
| 5 | **Review-site language** — not curation language | "画面震撼，音乐动人" | Prompt doesn't establish BigPRC's editorial voice |

---

## B. Optimized Prompt

```python
PROMPT_V2 = """你是 BigPRC 的数字资源策展编辑。

BigPRC 是一个数字资源策展库。用户来这里不是为了看评测，而是为了判断：
- 这个资源是否值得长期收藏？
- 和网上其他版本比，为什么选这一个？
- 下载前需要知道什么？

你的任务：根据已知信息，用编辑的判断力帮助用户做出选择。

═══════════════════════════════════════
资源信息（仅基于以下事实，不要推测）：
═══════════════════════════════════════
名称: {title}
类型: {category}
大小: {file_size}
平台: {platform}
版本: {version}
所属专题: {collections}
现有说明: {seo_desc}

═══════════════════════════════════════
写作规则：
═══════════════════════════════════════

1. 只基于以上信息写作。如果某个细节不在上述信息中，不要编造。
   例如：不知道拍摄技术就不要提拍摄技术。不知道作者就不要提作者。
   如果信息不足以做出判断，诚实地缩小推荐范围，不要用泛泛的夸奖填充。

2. 禁止使用以下词汇或类似表达：
   震撼、惊艳、必看、神作、强烈推荐、非常优秀、功能强大、
   最好用、必备、神器、全网最全、不容错过、巨好用

3. editor_recommendation (1-3句):
   像编辑在告诉朋友"为什么我选了这一个保留在库里"。
   重点：稀缺性、版本优势、专题内的定位、长期价值。
   不要写成内容简介——seo_desc 已经做了那个。

4. target_audience (1句):
   具体到用户场景。至少从以下选一种并细化：
   零基础入门 / 有基础进阶 / 专业从业者 / 学生 /
   内容创作者 / 开发者 / 家庭用户 / 教育者
   禁止："所有人""适合所有人""每个人"

5. strengths (2-3条):
   每条开头用 + 号。每条必须可验证，不能是主观感受。
   参考角度：
   - 版本稀缺：这个版本为什么比网上其他版本更好？
   - 完整性：是否包含了别人缺失的内容？
   - 可用性：下载后能否直接使用？是否需要额外配置？
   - 长期价值：为什么值得保存在硬盘里而不是在线观看？
   反面示例（禁止）：
   + 内容丰富  + 画质清晰  + 非常实用  + 讲解详细

6. caveats (1-3条):
   每条开头用 · 号。必须是用户在下载/使用前真正需要知道的信息。
   参考角度：
   - 技术限制：需要什么软件/硬件/系统？
   - 范围限制：这个资源不包含什么（用户可能误以为包含）？
   - 质量说明：和更新/更好的版本相比有什么差距？
   - 使用门槛：需要什么前置知识或技能？
   反面示例（禁止）：
   · 画质一般  · 文件较大  · 需要耐心观看

请输出严格 JSON（不要包含 markdown 代码块标记）：
{{"editor_recommendation":"...","target_audience":"...","strengths":["+ ...","+ ..."],"caveats":["· ...","· ..."]}}"""
```

---

## C. Minimum Code Change

In `editorial_pilot.py`, replace `PROMPT_A` and `PROMPT_B` with the single `PROMPT_V2` above, then update `generate_editorial()` to use it.

```python
# Before (lines 87-130): two prompt variants, ~45 lines
# After: single optimized prompt, ~60 lines

PROMPT_V2 = """..."""  # full text above

def generate_editorial(resource, prompt_variant="A"):
    # prompt_variant kept for CLI compatibility, always uses V2
    prompt = PROMPT_V2.format(...)
    ...
```

CLI `--prompt A` and `--prompt B` both map to V2 (backward compatible).

---

## D. Expected Output Example

### Input

```
名称: BBC地球脉动 行星地球 第一季+第二季 4K合集
类型: 纪录片
大小: 140.5 GB
平台: 夸克网盘
版本: 4K HDR
所属专题: BBC 自然纪录片
现有说明: BBC自然纪录片经典系列，David Attenborough解说...
```

### Before (current prompt — hypothetical bad output)

```json
{
  "editor_recommendation": "震撼人心的自然纪录片巨作！BBC《行星地球》系列以惊人的画质和深刻的叙事，带您领略地球最壮丽的自然奇观。这部纪录片不仅是一场视觉盛宴，更是对自然生态的深刻思考。无论您是纪录片爱好者还是普通观众，都会被深深吸引。",
  "target_audience": "纪录片爱好者、自然爱好者、所有对地球生态感兴趣的观众",
  "strengths": ["+ 画质震撼，4K HDR呈现极致细节", "+ 内容精彩，David Attenborough经典解说", "+ 非常全面，涵盖地球各类生态系统"],
  "caveats": ["· 文件较大，需要足够存储空间", "· 需要支持4K播放的设备"]
}
```

**Problems**: Fabricated "8K IMAX拍摄" → hallucination. "所有人" audience. Generic praise. Useless caveats.

### After (optimized prompt)

```json
{
  "editor_recommendation": "BBC《行星地球》第一季+第二季的4K合集版本。这个版本的价值在于完整性——两季一起收录，且都是4K HDR原盘压制，不是流媒体录制版。在中文互联网上，同时找到两季高质量版本并不容易，这个合集解决了分开搜索的麻烦。",
  "target_audience": "自然纪录片收藏者；有4K大屏电视、追求画质的家庭用户；地理/生物学科教师",
  "strengths": ["+ 两季完整收录，不需要分开寻找不同版本", "+ 4K HDR原盘压制，保留了暗部和高光的完整细节", "+ 双语字幕可切换，适合英语学习场景"],
  "caveats": ["· 140GB，建议选择性下载而非全量保存", "· HDR需要支持HDR的播放器和显示器，普通屏幕画面会偏灰", "· 第一季原始素材来自2006年，部分画面颗粒感较重（非压制问题）"]
}
```

**Improvements**: No fabrication. Specific audience. Verifiable strengths. Actionable caveats.
