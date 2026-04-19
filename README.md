# skills-repo

用于在多台设备之间同步可复用的 skills 仓库。

## 目录结构

- `codex/`：Codex 使用的 skills（`SKILL.md`）
- `claude-code/`：Claude Code 使用的 skills（`skill.md`）

## 使用流程

1. 在本仓库更新 skills。
2. 提交并推送到 GitHub。
3. 在其他电脑拉取最新版本。
4. 将对应目录同步到各工具的运行路径。

## 新电脑一键同步示例

先克隆仓库：

```powershell
git clone <你的skills仓库URL> "D:\File\skills-repo"
```

同步到 Codex：

```powershell
New-Item -ItemType Directory -Force -Path "D:\File\.codex\skills" | Out-Null
Copy-Item -Path "D:\File\skills-repo\codex\*" -Destination "D:\File\.codex\skills" -Recurse -Force
```

同步到 Claude Code：

```powershell
New-Item -ItemType Directory -Force -Path "D:\File\llm-wiki\Claude Code\skills" | Out-Null
Copy-Item -Path "D:\File\skills-repo\claude-code\*" -Destination "D:\File\llm-wiki\Claude Code\skills" -Recurse -Force
```
