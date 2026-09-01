# GPA — Git Push All

一键同步 dotfiles / 配置文件到 Git 仓库，并推送到多个远程仓库。

## 安装

```bash
# 克隆项目
git clone git@github.com:WongKaXing/gpa.git
cd gpa

# 使用 uv 安装为系统命令
uv tool install .
```

安装完成后，直接在终端使用 `gpa` 命令。

**依赖**：Python ≥ 3.12，纯标准库，无外部依赖。

## 快速开始

```bash
gpa init    # 首次运行，交互式配置向导
gpa         # 后续运行，进入交互菜单（或按设置直接推送）
gpa -a      # 直接推送所有仓库（自动使用已保存的配置文件）
gpa -c ~/.gitpush.toml   # 指定配置文件直接执行推送
gpa list    # 列出所有已配置的仓库
gpa push nvim   # 推送指定仓库（支持自定义仓库名或序号，如 gpa push 1）
```

配置文件路径会被系统自动记住（存储在 `~/.config/gitpush/state.json`），日常使用直接 `gpa -a` 即可一键推送全部仓库，无需再指定配置文件；`-c` 仅在需要临时切换配置文件时使用。

## 配置文件

默认配置文件位于 `~/.gitpush.toml`。支持两种同步方式：

**方式一：整目录同步（推荐）** — `sync_dir` 指定源目录，自动同步该目录下全部文件，仅需用 `exclude` 排除不需要的文件：

```toml
[defaults]
commit_template = "update {date}"     # 提交信息模板 {date} 会被替换为当前日期
exclude = [".DS_Store", "__pycache__", "*.pyc"]  # 全局排除规则

[[repos]]
name = "nvim"                         # 自定义仓库名（可中文，用于 gpa push <名称/序号>）
path = "~/Documents/Git/nvim/"        # Git 仓库本地路径
remotes = ["gitee", "github"]         # 远程仓库名列表
sync_dir = "~/.config/nvim"           # 同步整个目录到仓库根目录
exclude = ["*.tmp", "cache/"]         # 额外排除（合并全局排除）
```

**方式二：逐条映射（旧语法）** — `[[repos.files]]` 精确指定每个 source → dest：

```toml
[[repos]]
name = "dotfiles"
path = "~/Documents/Git/dotfiles/"
remotes = ["gitee", "github"]

[[repos.files]]
source = "~/.zshrc"                   # 源文件/目录
dest = "."                            # 目标相对路径（相对于仓库根目录）
```

两种方式可在同一仓库中并存。

## gpa 设置文件

gpa 自身的行为通过 `~/.config/gitpush/settings.toml` 配置。**首次运行 gpa 会自动生成带注释说明的模板文件**，列出全部可配置参数：

| 参数 | 可选值 | 默认 | 说明 |
|------|--------|------|------|
| `sort_order` | `asc` / `desc` / `config` | `asc` | 仓库显示与处理顺序：字母序 / 倒序 / 配置文件顺序 |
| `show_usage` | `true` / `false` | `true` | 执行 gpa（无参数）时是否显示用法说明 |
| `color` | `true` / `false` | `true` | 是否启用 ANSI 颜色输出 |
| `default_action` | `menu` / `push` | `menu` | gpa 无参数时的默认动作：进入交互菜单 / 直接推送全部仓库 |

修改后保存，下次运行 gpa 自动生效。

## 交互菜单

`gpa` 无参数运行时会显示 banner 和交互菜单：

```
1. 执行 Git Push — 同步并推送所有仓库
2. 推送指定仓库 — 选择单个仓库推送
3. 添加新的 Git 仓库 — 进入向导添加仓库
4. 管理已有仓库 — 查看详情 / 删除 / 重新配置
5. 重新运行配置向导 — 覆盖当前配置
q. 退出
```

### q 键导航

CLI 模式支持 `q` 键快速导航：

- **主菜单**：按 `q` 直接退出程序（菜单项 `q. 退出`）。
- **子菜单**（推送指定仓库、管理仓库、配置向导等）：按 `q` 返回上一个模块位置，一层层退回，最终回到主菜单。

配置向导中按 `q` 会取消当前流程（不写入任何修改），回到上一个菜单。

添加仓库时支持 Tab 路径自动补全，自动检测重复仓库。

## 命令行参数

| 参数 | 说明 |
|------|------|
| `gpa init` | 运行交互式配置向导 |
| `gpa -a` | 直接推送所有仓库（自动使用已保存的配置） |
| `gpa list` | 列出所有已配置的仓库 |
| `gpa push <名称或序号>` | 推送指定仓库（自定义仓库名，或排序后的序号如 `gpa push 1`） |
| `gpa -c <路径>` | 指定配置文件直接推送 |
| `gpa -v, --version` | 显示版本信息 |
| `gpa --dry-run` | 预览模式，仅显示将要执行的操作 |
| `gpa --verbose` | 详细输出 |
| `gpa -q, --quiet` | 静默模式，仅显示错误 |

## 工作流程

1. **文件同步** — 将配置文件中指定的源文件/目录复制到对应 Git 仓库
2. **Git 提交** — 按提交模板自动 `git add -A` 并 `git commit`
3. **推送远程** — 依次 `git push` 到配置的所有远程仓库

## 状态持久化

工具会记住上次使用的配置文件路径，存储在 `~/.config/gitpush/state.json`。首次使用后，直接运行 `gpa` 即可自动找到配置。
