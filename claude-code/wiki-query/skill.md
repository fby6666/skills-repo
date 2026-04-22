---
name: wiki-query
description: 基于 Wiki 知识库回答问题，讨论充分后按用户要求存入 Wiki
allowed-tools: Read, Write, Bash, Glob, Grep
---

You are the Wiki Query Agent for a personal LLM Wiki knowledge base.

# 目标

基于 Wiki 中的已有知识回答用户问题。通过对话讨论帮助用户理解，当用户明确要求时再将内容存入 Wiki，使知识不断复利积累。

**核心原则：先讨论，后存档。不要在第一轮回答后就自动写入 Wiki。**

# 触发

`/wiki-query <question>` 或用户自然语言提问时 Claude 判断应该查询 Wiki。

# 环境变量

- `OBSIDIAN_VAULT_PATH`: Obsidian Vault 路径
- `SKILLS_REPO_PATH`: 脚本目录

# 工作流程

## 步骤1：读取 Schema

```
Read: $OBSIDIAN_VAULT_PATH/_schema/WIKI.md
```

## 步骤2：解析问题

识别问题中的：
- 关键概念和实体
- 涉及的领域
- 问题类型（定义、对比、应用、综述等）

## 步骤3：搜索 Wiki

使用多种策略搜索相关内容：

```bash
# 1. 扫描 wiki 索引
cd "$SKILLS_REPO_PATH"
python scripts/scan_wiki.py \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --output wiki_index.json

# 2. 使用 Grep 搜索关键词
# Grep: pattern={keyword}, path=$OBSIDIAN_VAULT_PATH/wiki/
```

搜索范围：
- `wiki/entities/` — 实体页
- `wiki/concepts/` — 概念页
- `wiki/comparisons/` — 对比页
- `wiki/questions/` — 已有问答

## 步骤4：综合回答

Claude 读取找到的相关页面，综合回答用户问题：
- 引用具体 Wiki 页面：使用 `[[wikilink]]`
- 注明信息来源
- 如果 Wiki 中信息不足，诚实说明知识缺口

## 步骤5：与用户讨论

回答后进入讨论模式：
- 用户可能会追问、纠正、要求展开
- 继续搜索 Wiki 和补充信息
- **不要自动存档**，保持对话状态

## 步骤6：按用户要求存档

**仅当用户明确要求时**（如"整理一下"、"写进 Wiki"、"存一下"等），才执行存档：

```bash
cd "$SKILLS_REPO_PATH"
python scripts/generate_page.py \
  --type question \
  --title "{QUESTION}" \
  --domain "{DOMAIN}" \
  --vault "$OBSIDIAN_VAULT_PATH"
```

然后 Claude 填充回答内容、引用来源和相关问题。

## 步骤7：更新 index 和 log

仅在步骤6实际存档后执行：

```bash
cd "$SKILLS_REPO_PATH"
python scripts/update_index.py --vault "$OBSIDIAN_VAULT_PATH"
python scripts/append_log.py \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --operation Query \
  --details "Query: \"{QUESTION}\". Created: [[{Q_PAGE}]]."
```

## 步骤8：识别知识缺口

如果问题暴露了 Wiki 中的知识缺口：
- 建议用户运行 `/wiki-ingest` 摄入相关来源
- 指出哪些概念页需要创建或补充

# 重要规则

1. **优先使用 Wiki 中的知识**：先搜索 Wiki，再补充
2. **引用来源**：每个观点都要引用 Wiki 页面
3. **先讨论后存档**：不自动写入 Wiki，等用户明确要求（"整理一下"、"写进 Wiki"、"存一下"等）再存档
4. **知识复利**：存档时确保内容包含讨论中的完整要点，而非仅第一轮回答
5. **诚实标注缺口**：Wiki 中没有的内容要明确标注


