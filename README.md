# skills-repo

用于在多台设备之间同步可复用的 skills 与配套脚本。

## 目录结构

- `codex/`：Codex 使用的 skills（`SKILL.md`）
- `claude-code/`：Claude Code 使用的 skills（`skill.md`）
- `scripts/`：skills 运行时调用的脚本（`python scripts/*.py`）

## 使用流程

1. 在本仓库更新 skills 或脚本。
2. 提交并推送到 GitHub。
3. 在其他电脑拉取最新版本。
4. 将 `codex/`、`claude-code/` 同步到各自工具目录。
5. 在使用技能前，先确保 `scripts/` 依赖已安装。

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

## 脚本依赖

在仓库根目录执行：

```powershell
pip install -r .\scripts\requirements.txt
```

说明：

- skills 文档中的 `python scripts/xxx.py` 命令，默认是在本仓库根目录运行。
- `scripts/wiki_index.json` 一类文件属于运行产物，不建议纳入版本控制。
