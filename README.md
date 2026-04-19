# skills-repo

用于在多台设备之间同步可复用的 skills 与配套脚本。

## 目录结构

- `codex/`：Codex 使用的 skills（`SKILL.md`）
- `claude-code/`：Claude Code 使用的 skills（`skill.md`）
- `scripts/`：skills 运行时调用的脚本（`python scripts/*.py`）

## 环境变量

所有 skill 都依赖 `SKILLS_REPO_PATH` 环境变量，指向本仓库的克隆路径。

**macOS / Linux**（写入 `~/.zshrc` 或 `~/.bashrc`）：

```bash
export SKILLS_REPO_PATH="$HOME/skills-repo"
```

**Windows**（PowerShell profile）：

```powershell
$env:SKILLS_REPO_PATH = "D:\File\skills-repo"
```

设置后重启终端或 `source ~/.zshrc` 使其生效。

## 使用流程

1. 在本仓库更新 skills 或脚本。
2. 提交并推送到 GitHub。
3. 在其他电脑拉取最新版本。
4. 将 `codex/`、`claude-code/` 同步到各自工具目录。
5. 在使用技能前，先确保 `scripts/` 依赖已安装，且 `SKILLS_REPO_PATH` 已设置。

## 新电脑一键同步示例

### macOS / Linux

```bash
# 克隆仓库
git clone git@github.com:fby6666/skills-repo.git "$HOME/skills-repo"

# 同步到 Codex
mkdir -p "$HOME/.codex/skills"
cp -r "$HOME/skills-repo/codex/"* "$HOME/.codex/skills/"

# 同步到 Claude Code（按实际项目路径调整）
CLAUDE_SKILLS="$HOME/your-project/.claude/skills"
mkdir -p "$CLAUDE_SKILLS"
cp -r "$HOME/skills-repo/claude-code/"* "$CLAUDE_SKILLS/"
```

### Windows (PowerShell)

```powershell
# 克隆仓库
git clone git@github.com:fby6666/skills-repo.git "D:\File\skills-repo"

# 同步到 Codex
New-Item -ItemType Directory -Force -Path "D:\File\.codex\skills" | Out-Null
Copy-Item -Path "D:\File\skills-repo\codex\*" -Destination "D:\File\.codex\skills" -Recurse -Force

# 同步到 Claude Code（按实际项目路径调整）
$ClaudeSkills = "D:\File\your-project\.claude\skills"
New-Item -ItemType Directory -Force -Path $ClaudeSkills | Out-Null
Copy-Item -Path "D:\File\skills-repo\claude-code\*" -Destination $ClaudeSkills -Recurse -Force
```

## 脚本依赖

```bash
# macOS / Linux
pip install -r scripts/requirements.txt

# Windows
pip install -r .\scripts\requirements.txt
```

说明：

- skills 文档中的 `python scripts/xxx.py` 命令，会先 `cd "$SKILLS_REPO_PATH"` 再执行。
- `scripts/wiki_index.json` 一类文件属于运行产物，不建议纳入版本控制。
