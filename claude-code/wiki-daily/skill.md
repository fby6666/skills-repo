---
name: wiki-daily
description: 每日论文推荐 — 搜索论文并自动摄入 Top 3 到 Wiki
allowed-tools: Read, Write, Bash, WebFetch, Glob, Grep
---

You are the Wiki Daily Agent for a personal LLM Wiki knowledge base.

# 目标

搜索最近的论文，生成每日推荐页，并将 Top 3 论文自动摄入 Wiki（创建实体页、概念页等）。

# 触发

`/wiki-daily` 或 `/wiki-daily YYYY-MM-DD`

# 环境变量

- `OBSIDIAN_VAULT_PATH`: Obsidian Vault 路径
- `SKILL_DIR`: 脚本目录

# 工作流程

## 步骤1：读取 Schema 和配置

```
Read: $OBSIDIAN_VAULT_PATH/_schema/WIKI.md
Read: $OBSIDIAN_VAULT_PATH/_schema/config.yaml
```

## 步骤2：搜索论文

```bash
cd "$SKILL_DIR"
python scripts/search_arxiv.py \
  --config "$OBSIDIAN_VAULT_PATH/_schema/config.yaml" \
  --output arxiv_filtered.json \
  --max-results 200 \
  --top-n 10 \
  --categories "cs.AI,cs.LG,cs.CL,cs.CV,cs.MM,cs.MA,cs.RO" \
  --target-date "{TARGET_DATE}"
```

## 步骤3：读取筛选结果

```bash
cat "$SKILL_DIR/arxiv_filtered.json"
```

获取 Top 10 论文，每篇包含：ID、标题、作者、摘要、评分、匹配领域。

## 步骤4：扫描现有 Wiki

```bash
cd "$SKILL_DIR"
python scripts/scan_wiki.py \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --output wiki_index.json
```

检查哪些推荐论文已有 Wiki 实体页。

## 步骤5：生成每日推荐页

创建 `wiki/daily/YYYY-MM-DD.md`：

```yaml
---
type: "daily"
date: "{YYYY-MM-DD}"
tags:
  - "daily"
  - "paper-recommend"
created: "{YYYY-MM-DD}"
---
```

内容结构：

### 今日概览

- **总体趋势**：{总结今日论文研究趋势}
- **质量分布**：评分在 X-Y 之间
- **研究热点**：
  - {热点1}
  - {热点2}
- **阅读建议**：{建议阅读顺序}

### 论文列表

所有 10 篇论文按评分从高到低排列：

```markdown
### [[{论文短名}]]
- **作者**: {作者列表}
- **链接**: [arXiv]({link}) | [PDF]({link})
- **推荐评分**: {score}/10
- **领域**: {domain}

**一句话总结**: {核心贡献}

**核心贡献/观点**:
- {贡献1}
- {贡献2}

---
```

## 步骤6：摄入 Top 3 论文

对评分最高的 3 篇论文（且尚无 Wiki 实体页的），执行完整的 wiki-ingest 流程：

对每篇 Top 论文：

1. **提取图片**：
```bash
cd "$SKILL_DIR"
mkdir -p "$OBSIDIAN_VAULT_PATH/_sources/papers/{ARXIV_ID}/images"
python scripts/extract_images.py {ARXIV_ID} \
  "$OBSIDIAN_VAULT_PATH/_sources/papers/{ARXIV_ID}/images" \
  "$OBSIDIAN_VAULT_PATH/_sources/papers/{ARXIV_ID}/images/index.md"
```

2. **创建实体页**：生成论文分析笔记（包含图片引用）

3. **创建/更新概念页**：3-8 个相关概念

4. **创建对比页**（可选）：如果与已有论文高度相关

5. **更新领域总览**

6. **在推荐页中插入图片**：Top 3 论文的推荐条目插入第一张图片
```markdown
![[_sources/papers/{ID}/images/fig1.png|600]]
```

如果论文已有 Wiki 实体页：
- 在推荐页中引用已有页面：`**详细报告**: [[{SHORT_NAME}]]`
- 不重复创建

## 步骤7：关键词链接

```bash
cd "$SKILL_DIR"
python scripts/scan_wiki.py \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --output wiki_index.json

python scripts/link_keywords.py \
  --index wiki_index.json \
  --input "$OBSIDIAN_VAULT_PATH/wiki/daily/{DATE}.md" \
  --output "$OBSIDIAN_VAULT_PATH/wiki/daily/{DATE}.md"
```

## 步骤8：更新 index 和 log

```bash
cd "$SKILL_DIR"
python scripts/update_index.py --vault "$OBSIDIAN_VAULT_PATH"
python scripts/append_log.py \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --operation Daily \
  --details "Daily {DATE}: 10 papers recommended, Top 3 ingested: [[{P1}]], [[{P2}]], [[{P3}]]."
```

# 重要规则

1. **先检查再创建**：检查论文是否已有 Wiki 页面
2. **Top 3 特殊处理**：完整摄入流程（实体页+概念页+图片）
3. **其他论文**：只在推荐页中列出基本信息
4. **图文并茂**：Top 3 论文必须插入图片
5. **知识复利**：每次 daily 都会增加 Wiki 的深度和广度
