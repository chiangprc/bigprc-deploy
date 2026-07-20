# BigPRC v2.0 数据层升级完成报告

> **完成日期**: 2026-07-20
> **状态**: P0-B 数据层 + P1 产品层 全面闭环

---

## 1. 升级总览

```
v1.x (旧)                              v2.0 (新)
─────────────────────────────────      ─────────────────────────────────
Excel → SQLite 单表                     Excel → SQLite 10 表 规范化
resources 表 17 列                      resources(22列) + resource_content + metrics + access + collections + tags
无分类元数据                             AI 分类 15 类 + 40+ 子类型
无 AI 内容                              AI SEO 四字段全覆盖 (1760/1760)
无标签系统                               4500+ 原子化标签
无专题策展                               16 个策展专题 + 792 条关联
tag 分类页                                collection 专题页 + FAQ
1267 条资源                              1760 条资源
4 个 Python 脚本                          12 个 Python 脚本
```

---

## 2. 数据库架构 (v2)

### 核心表结构

| 表名 | 用途 | 记录数 |
|------|------|--------|
| `resources` | 主资源表 (22 列含 category/platform/file_format) | 1,760 |
| `resource_content` | AI 内容层 (tagline/summary/keywords/reason/editor_status) | 1,760 |
| `resource_metrics` | 行为指标 (view/click/fav/rating) | 1,760 |
| `resource_access` | 访问入口 (source_url/short_url/password) | ~3,520 |
| `collections` | 专题定义 (rule_json/is_featured) | 16 |
| `collection_content` | 专题 SEO (intro/seo_title/seo_desc/faq_json) | 16 |
| `resource_collections` | 资源-专题关联 | 792 |
| `tags` | 标签词表 (name/slug/type/parent_id/count) | ~4,564 |
| `resource_tags` | 资源-标签关联 (score/source) | ~9,982 |
| `tag_aliases` | 标签别名归一化映射 | 9 |
| `_migrations` | 迁移版本记录 | 12 |

### 迁移历史

| 编号 | 文件 | 说明 |
|------|------|------|
| 001 | `create_schema_version` | 版本追踪表 |
| 002 | `resources_v2` | 新增 v2 字段 |
| 003 | `resource_content` | 内容拆分表 |
| 004 | `resource_metrics` | 行为指标表 |
| 005 | `resource_access` | 访问入口表 |
| 006 | `collections` | 合集体系 + 9 种子 |
| 007 | `indexes` | 性能索引 |
| 008 | `validate_v2` | 完整性验证 |
| 009 | `tags` | 标签系统 |
| 010 | `tag_aliases` | 别名归一化 |
| 011 | `tag_hierarchy` | parent_id + tag_type |
| 012 | `collection_rules` | rule_json + score |

---

## 3. 分类体系

### 资源分类 (15 类)

| 分类 | 数量 | 说明 |
|------|------|------|
| 传统文化 | 538 | 道教/佛教/古籍/中医 |
| 自然科学 | 407 | BBC/Disc/NatGeo/IMAX 纪录片 |
| 历史文化 | 262 | 战争/文明/哲学 |
| 软件工具 | 146 | Android/Windows 应用 |
| 商业职场 | 78 | 运营/营销/管理 |
| 课程学习 | 76 | 视频教程/培训 |
| 艺术设计 | 61 | 建筑/美术/音乐 |
| 旅行地理 | 60 | 旅行纪录片/城市 |
| 儿童教育 | 54 | 英语启蒙/动画 |
| 设计创意 | 22 | 设计工具/素材 |
| 电子书籍 | 21 | 词典/文献/套装书 |
| 美食生活 | 19 | 园艺/手工/健康 |
| 编程开发 | 7 | IDE/框架/开源 |
| AI 技术 | 6 | AI 工具/模型 |
| 游戏娱乐 | 3 | 游戏/MOD |

### 平台分布

| 平台 | 数量 |
|------|------|
| 视频 | 925 |
| PDF | 552 |
| Android | 106 |
| 电子书 | 70 |
| Windows | 48 |
| 音频 | 26 |
| 网页 | 12 |
| 其他 | 21 |

---

## 4. AI 内容流水线

### 数据流

```
Excel (pantools_export.xlsx)
  ↓ pantools_sync_v2.py
resources (category/platform/file_format)
  ↓ ai_classifier.py (P0-B.2.5)
resources + resource_content.resource_type  ← 分类完成
  ↓ ai_seo_writer.py --round 1 (P0-B.3)
resource_content (tagline + ai_summary + ai_keywords)
  ↓ ai_seo_writer.py --round 2 (P0-B.3)
resource_content (ai_reason_candidates)
  ↓ ai_tag_generator.py (P1-2)
tags + resource_tags                          ← 标签完成
  ↓ tag_normalize.py (P1-2.5)
tag_aliases (碎片归一化)                       ← 治理完成
  ↓ collection_generator.py (P1-3)
collections + resource_collections            ← 专题完成
  ↓ collection_faq.py (Phase 3.1)
collection_content.faq_json                   ← FAQ 完成
  ↓ auto_generate.py
静态 HTML + JSON + sitemap                    ← 部署
```

### Round 1 生成质量

| 字段 | 覆盖率 | 平均长度 | 质量 |
|------|--------|----------|------|
| tagline | 1760/1760 (100%) | 15.7 字 | ✅ 中文策展推荐语 |
| ai_summary | 1760/1760 (100%) | 35.5 字 | ✅ 无营销词 |
| ai_keywords | 1760/1760 (100%) | ~6 个 | ✅ 搜索价值 |
| ai_reason_candidates | 1760/1760 (100%) | ~3-5 条 | ✅ 事实性 |

### Tag 系统

- 1760 条资源 → 4,564 个唯一标签 → 归一化后 ~4,550 个
- 平均 2.6 个标签/资源
- Top 20 标签：纪录片(733), BBC(389), 动物(175), 自然(173), 电子书(171), 道教(157), 课程(137), 历史(100), 古籍(97), 道家(89), 符箓(83), 国家地理(75), 符咒(74), IMAX(72)...

---

## 5. Python 脚本清单

| 脚本 | 阶段 | 功能 |
|------|------|------|
| `pantools_sync_v2.py` | P0-B.1 | Excel → SQLite v2 多表同步 |
| `migration.py` | P0-B.1 | 数据库迁移管理 (status/plan/up/validate/backup) |
| `ai_classifier.py` | P0-B.2.5 | AI 资源分类 (category/platform/resource_type/file_format) |
| `ai_seo_writer.py` | P0-B.3 | AI SEO 内容生成 (tagline/summary/keywords/reason) |
| `seo_content_cleanup.py` | P0-C | 残留营销词精准删除 (SQL 级，不调 AI) |
| `ai_tag_generator.py` | P1-2 | AI 标签提取 + tags/resource_tags 写入 |
| `tag_normalize.py` | P1-2.5 | 标签归一化 (品牌统一/拼写修复/复合拆分) |
| `collection_generator.py` | P1-3 | 专题自动生成 + resource_collections 填充 |
| `collection_faq.py` | Phase 3.1 | AI 生成专题 FAQ 写入 faq_json |
| `auto_generate.py` | 静态生成 | 全站 HTML + JSON + sitemap + 专题页 |
| `check_dead_links.py` | 运维 | 死链检测 |
| `local_server.py` | 开发 | 本地预览服务器 |

---

## 6. 模板系统 (Jinja2)

| 模板 | 路径 | 用途 |
|------|------|------|
| `layout.html` | templates/ | 基础布局 (dark/light 主题) |
| `detail.html` | templates/ | 资源详情页 |
| `list.html` | templates/ | 资源列表页 + tag 分类页 |
| `collection.html` | templates/ | 专题策展页 (hero + FAQ + 搜索) |
| `collection_index.html` | templates/ | 专题索引导航页 |
| `transit.html` | templates/ | 5 秒反滥用跳转中转页 |

---

## 7. 专题清单 (16 个)

| ID | 标题 | 资源数 | 规则 |
|----|------|--------|------|
| bbc-nature | BBC 自然纪录片 | 315 | BBC + 纪录片 |
| taoist-rituals | 道教符箓科仪 | 70 | 道教 AND (符箓 OR 符咒 OR 科仪) |
| imax-doc | IMAX 巨幕纪录片 | 65 | IMAX + 纪录片 |
| discovery-science | Discovery 科学探索 | 42 | Discovery + 纪录片 |
| taoist-classics | 道家经典文献 | 41 | 道教 + 古籍 |
| android-tools | Android 实用工具 | 40 | Android |
| space-universe | 宇宙探索 | 40 | 宇宙 |
| ocean-wildlife | 海洋与野生动物 | 38 | 海洋 + 动物 |
| bbc-history | BBC 历史纪录片 | 36 | BBC + 历史 |
| natgeo-nature | 国家地理 自然奇观 | 24 | 国家地理 + 自然 |
| taoist-manuscripts | 道家手抄孤本 | 19 | 手抄本 + 道教 |
| video-editing | 视频剪辑工具包 | 18 | 视频剪辑 |
| war-history | 战争与历史 | 13 | 战争 + 历史 |
| ai-tools | AI 效率工具 | 12 | AI OR ChatGPT OR Claude |
| windows-software | Windows 效率软件 | 12 | Windows |
| english-learning | 英语学习资源 | 7 | 英语 + 课程 |

---

## 8. CLI 命令速查

```bash
# === 数据同步 ===
python3 pantools_sync_v2.py           # Excel → DB 同步
python3 pantools_sync_v2.py --dry-run # 预览模式

# === 数据库迁移 ===
python3 migration.py status           # 查看版本
python3 migration.py up               # 执行迁移
python3 migration.py validate         # 完整性检查

# === AI 分类 ===
python3 ai_classifier.py --plan       # 待分类统计
python3 ai_classifier.py --limit 10   # 灰度测试
python3 ai_classifier.py              # 全量分类

# === AI SEO 生成 ===
python3 ai_seo_writer.py --plan       # 待生成统计
python3 ai_seo_writer.py --round 1 --limit 10  # 灰度
python3 ai_seo_writer.py --round 1 --force     # Round1 全量
python3 ai_seo_writer.py --round 2 --force     # Round2 全量
python3 ai_seo_writer.py --audit               # 质量巡检
python3 ai_seo_writer.py --repair              # 修复违规词

# === 标签系统 ===
python3 ai_tag_generator.py --plan    # 待标记统计
python3 ai_tag_generator.py           # 全量提取
python3 tag_normalize.py --plan       # 预览归一化
python3 tag_normalize.py              # 执行归一化

# === 专题系统 ===
python3 collection_generator.py --plan   # 预览专题
python3 collection_generator.py --rebuild # 清空重建
python3 collection_faq.py --plan         # 预览 FAQ
python3 collection_faq.py --limit 3      # 灰度

# === 静态生成 ===
python3 auto_generate.py              # 全站生成 (含专题/FAQ/sitemap)
```

---

## 9. 前端静态文件

| 路径 | 说明 |
|------|------|
| `/` | 首页 (搜索入口 + 分类标签) |
| `/list.html` | 全量资源列表 |
| `/tag_{cat}.html` | 15 个分类标签页 |
| `/collection/index.html` | 专题索引导航 |
| `/collection/{slug}.html` | 16 个专题详情页 |
| `/go/{res_id}` | 资源跳转中转页 |
| `/post/{res_id}.html` | 资源详情页 (历史) |
| `/index.json` | 前端搜索数据 |
| `/collections.json` | 首页专题卡片数据 |
| `/sitemap.xml` | SEO 站点地图 |
