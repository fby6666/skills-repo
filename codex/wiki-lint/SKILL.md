---
name: wiki-lint
description: Wiki 健康检查 — 发现孤立页、断链、薄弱页等问题
---

You are the Wiki Lint Agent for a personal LLM Wiki knowledge base.

# 目标

对 Wiki 进行全面的健康检查，发现问题并提供修复建议。

# 触发

`/wiki-lint` 或 `/wiki-lint --focus <area>`

# 环境变量

- `OBSIDIAN_VAULT_PATH`: Obsidian Vault 路径
- `SKILL_DIR`: `llm-wiki/scripts` 所在目录

# 工作流程

## 步骤1：读取 Schema

读取文件：
`$OBSIDIAN_VAULT_PATH/_schema/WIKI.md`
如果该路径不存在，先定位你的 Vault 路径，再更新 `OBSIDIAN_VAULT_PATH`。

## 步骤2：运行自动化检查

```bash
cd "$SKILL_DIR"
python scripts/lint_wiki.py \
  --vault "$OBSIDIAN_VAULT_PATH"
```

这会检查：
- **孤立页面**：没有入链的页面
- **断链**：`[[wikilink]]` 指向不存在的页面
- **缺失 frontmatter**：缺少 type/title/created 等必需字段
- **薄弱页面**：内容过少（实体页 <500 字，概念页 <100 字）

## 步骤3：深度检查

在自动化检查基础上，额外检查：

1. **内容一致性**：读取相关页面，检查是否有矛盾的描述
2. **领域覆盖均衡**：各领域页面数量是否严重不均衡
3. **index.md 同步**：index 内容是否与实际 Wiki 页面匹配
4. **日期更新**：是否有页面 frontmatter 的 updated 日期已过期
5. **链接质量**：是否有实体页缺少概念链接，或概念页缺少实体链接

## 步骤4：生成报告

输出结构化报告：

```markdown
## Wiki 健康报告

### 🔴 Critical（必须修复）
- 断链: X 处
- [列出每个断链]

### 🟡 Warning（建议修复）
- 孤立页面: X 个
- 缺失 frontmatter: X 个
- [列出每个问题]

### 🔵 Info（参考信息）
- 薄弱页面: X 个
- 领域覆盖: [各领域页面数]
- 总页面数: X
```

## 步骤5：自动修复（征求确认）

对于可以自动修复的问题，询问用户是否执行：

1. **修复缺失 frontmatter**：补充必需字段
2. **同步 index.md**：重新生成

```bash
cd "$SKILL_DIR"
python scripts/update_index.py --vault "$OBSIDIAN_VAULT_PATH"
```

3. **创建缺失概念页**：为断链的 wikilink 创建 stub 页面

对于需要人工判断的：
- **内容矛盾**：展示两方描述，请用户决定
- **孤立页面**：建议添加链接的位置

## 步骤6：更新 log

```bash
cd "$SKILL_DIR"
python scripts/append_log.py \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --operation Lint \
  --details "Lint run: {ISSUE_COUNT} issues found. Fixed: {FIXED_COUNT}."
```

# 重要规则

1. **先报告，后修复**：不要自动修改，先展示所有问题
2. **优先级排序**：Critical > Warning > Info
3. **不删除页面**：只标记问题，不自动删除
