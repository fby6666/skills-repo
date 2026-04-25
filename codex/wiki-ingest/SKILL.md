---
name: wiki-ingest
description: 将新来源（论文/文章/想法等）摄入到 LLM Wiki 知识库中
---

You are the Wiki Ingest Agent for a personal LLM Wiki knowledge base.

# 目标

将新来源（论文、网页文章、书籍笔记、个人想法等）摄入到 Wiki 中，创建/更新实体页、概念页、对比页和领域总览页，并维护 index 和 log。

**核心原则：每次摄入应触达 10-15 个页面。**

# 触发

`/wiki-ingest <source>` 其中 source 可以是：
- arXiv ID（如 `2412.01007`）
- URL（网页文章）
- 本地文件路径（PDF、markdown）
- 自由文本（个人想法、聊天记录摘要）

# 环境变量

- `OBSIDIAN_VAULT_PATH`: Obsidian Vault 路径
- `SKILLS_REPO_PATH`: `skills-repo（包含 scripts/）` 所在目录

# 工作流程

## 步骤0：读取 Schema

**必须首先执行**：读取 `_schema/WIKI.md` 了解所有规则和约定。

读取文件：
`$OBSIDIAN_VAULT_PATH/_schema/WIKI.md`
如果该路径不存在，先定位你的 Vault 路径，再更新 `OBSIDIAN_VAULT_PATH`。

## 步骤1：识别来源类型

根据输入判断来源类型：

| 输入格式 | 来源类型 | 处理方式 |
|----------|----------|----------|
| `XXXX.XXXXX` 格式 | arXiv 论文 | 下载 PDF，获取元数据 |
| `http://` 或 `https://` | 网页文章 | WebFetch 抓取内容 |
| 本地 `.pdf` 路径 | 本地文档 | 直接读取 |
| 其他文本 | 个人想法/笔记 | 直接作为内容 |

## 步骤2：存储原始资料到 `_sources/`

### 论文类型

```bash
# 创建目录
mkdir -p "$OBSIDIAN_VAULT_PATH/_sources/papers/{ARXIV_ID}/images"

# 提取图片
cd "$SKILLS_REPO_PATH"
python scripts/extract_images.py {ARXIV_ID} \
  "$OBSIDIAN_VAULT_PATH/_sources/papers/{ARXIV_ID}/images" \
  "$OBSIDIAN_VAULT_PATH/_sources/papers/{ARXIV_ID}/images/index.md"
```

### 网页文章类型

```bash
cd "$SKILLS_REPO_PATH"
python scripts/fetch_article.py "{URL}" --vault "$OBSIDIAN_VAULT_PATH"
```

脚本会自动：
- 下载文章中的图片到 `_sources/articles/{title}/images/`
- 在 markdown 中用 Obsidian embed 格式引用图片：`![[_sources/articles/{title}/images/fig1.jpg|800]]`
- 对小红书等图文类网页，从嵌入的 JSON 数据中提取高清图片 URL
- 生成 `images/index.md` 图片索引

**输出目录结构**：
```
_sources/articles/{title}/
  {title}.md          # 文章 markdown（含图片 embed）
  images/
    fig1.jpg
    fig2.jpg
    ...
    index.md          # 图片索引
```

**分析图文类文章时**：对于图片承载主要内容的文章（如小红书图文笔记、技术博客幻灯片），你必须先读取 `images/` 目录中的图片来理解文章完整内容，而不是仅凭文字描述推测。这能避免 wiki 页面出现幻觉。

## 步骤3：扫描现有 Wiki

```bash
cd "$SKILLS_REPO_PATH"
python scripts/scan_wiki.py \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --output wiki_index.json
```

读取 `wiki_index.json` 了解现有页面，避免重复创建。

## 步骤4：分析来源，确定需要创建/更新的页面

你分析来源内容，决定：

1. **实体页**：创建新的实体页（论文/文章/书/工具）
   - **论文** -> `entity/paper`
   - **网页文章** -> `entity/article`（类似 paper 实体页，包含一句话总结、内容概要、关键论点、涉及概念等）
2. **概念页**：该来源涉及哪些概念？
   - 哪些概念页已存在？→ 更新
   - 哪些概念页需要新建？→ 创建
   - 目标：每篇论文 3-8 个概念页
3. **对比页**：是否有密切相关的实体可以对比？
4. **领域总览**：是否需要更新领域总览？

## 步骤5：创建/更新页面

### 5.1 创建实体页

#### 论文类型

使用脚本生成骨架：

```bash
cd "$SKILLS_REPO_PATH"
python scripts/generate_page.py \
  --type entity/paper \
  --title "{PAPER_TITLE}" \
  --paper-id "{ARXIV_ID}" \
  --authors "{AUTHORS}" \
  --domain "{DOMAIN}" \
  --vault "$OBSIDIAN_VAULT_PATH"
```

然后你读取生成的骨架，填充详细分析内容：
- 一句话总结
- 摘要翻译（英文+中文）
- 研究问题与动机
- 方法（核心思想+架构+创新）
- 实验结果
- 深度分析
- 评分

**图片引用**：使用 `![[_sources/papers/{ID}/images/fig1.png|800]]` 格式。

#### 网页文章类型

使用脚本生成骨架：

```bash
cd "$SKILLS_REPO_PATH"
python scripts/generate_page.py \
  --type entity/article \
  --title "{ARTICLE_TITLE}" \
  --url "{URL}" \
  --author "{AUTHOR}" \
  --platform "{PLATFORM}" \
  --domain "{DOMAIN}" \
  --vault "$OBSIDIAN_VAULT_PATH"
```

然后你读取原始文章（特别是 `_sources/articles/{title}/images/` 中的图片）后填充：
- 一句话总结
- 内容概要（文章的完整结构和核心论述）
- 关键论点与数据（包含具体公式、实验数据、关键图表引用）
- 涉及的概念与论文（`[[wikilinks]]` 串联）
- 评价

**图片引用**：使用 `![[_sources/articles/{title}/images/fig1.jpg|800]]` 格式。

### 5.2 创建/更新概念页

对于每个涉及的概念：

- **如果概念页已存在**：读取现有内容，在「在具体工作中的应用」部分添加新条目
- **如果概念页不存在**：创建新的概念页

```bash
cd "$SKILLS_REPO_PATH"
python scripts/generate_page.py \
  --type concept \
  --title "{CONCEPT_NAME}" \
  --domain "{DOMAIN}" \
  --vault "$OBSIDIAN_VAULT_PATH"
```

然后你填充内容。

### 5.3 创建对比页（可选）

如果发现两个密切相关的实体：

```bash
cd "$SKILLS_REPO_PATH"
python scripts/generate_page.py \
  --type comparison \
  --title "{ENTITY_A} vs {ENTITY_B}: {TOPIC}" \
  --domain "{DOMAIN}" \
  --vault "$OBSIDIAN_VAULT_PATH"
```

### 5.4 更新领域总览（可选）

读取对应的 `wiki/domains/{domain}/_overview.md`，添加新论文/概念的链接。

## 步骤6：自动关键词链接

```bash
cd "$SKILLS_REPO_PATH"
# 先重新扫描索引
python scripts/scan_wiki.py \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --output wiki_index.json

# 对每个新创建/更新的文件执行关键词链接
python scripts/link_keywords.py \
  --index wiki_index.json \
  --input "{FILE_PATH}" \
  --output "{FILE_PATH}"
```

关键词链接仅用于**正文区**，不得改写 frontmatter（如 `title/aliases/domains/tags/source_path`）。
若发现 frontmatter 出现 `[[wikilink]]` 污染，先修复脚本或清洗元数据，再继续摄入流程。

## 步骤7：更新 index.md 和 log.md

```bash
cd "$SKILLS_REPO_PATH"
# 更新 index
python scripts/update_index.py --vault "$OBSIDIAN_VAULT_PATH"

# 追加 log
python scripts/append_log.py \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --operation Ingest \
  --details "Ingested [[{ENTITY_NAME}]] (source: {SOURCE_INFO}). Created: {NEW_PAGES}. Updated: {UPDATED_PAGES}."
```

## 步骤8：输出摘要

向用户展示：
- 创建了哪些页面
- 更新了哪些页面
- 发现了哪些关键概念和关系
- 建议后续可以做什么

# 重要规则

1. **读取 Schema 优先**：每次操作前必须读取 `_schema/WIKI.md`
2. **检查现有页面**：创建前先搜索是否已存在
3. **10-15 页面**：每次摄入目标触达 10-15 个页面
4. **图文并茂**：论文实体页引用 `![[_sources/papers/{ID}/images/fig1.png|800]]`；网页文章的 wiki 页面可引用 `![[_sources/articles/{title}/images/fig1.jpg|800]]`。图文类文章必须先读取图片再撰写 wiki 内容
5. **混合语言**：正文中文，技术术语保留英文
6. **wikilinks**：所有提到的概念和实体都要使用 `[[wikilink]]`
7. **不覆盖用户内容**：`%% user %%` 标记的区域不修改
8. **保持 frontmatter 完整**：所有字符串值用双引号
9. **更新 updated 字段**：修改页面时更新 frontmatter 中的 `updated` 日期
