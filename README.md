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
gpa         # 后续运行，进入交互菜单
gpa -a      # 直接推送所有仓库（自动使用已保存的配置文件）
gpa -c ~/.gitpush.toml   # 指定配置文件直接执行推送
gpa list    # 列出所有已配置的仓库
gpa push nvim   # 推送指定仓库
```

配置文件路径会被系统自动记住（存储在 `~/.config/gitpush/state.json`），日常使用直接 `gpa -a` 即可一键推送全部仓库，无需再指定配置文件；`-c` 仅在需要临时切换配置文件时使用。

## 配置文件

默认配置文件位于 `~/.gitpush.toml`，格式如下：

```toml
[defaults]
commit_template = "update {date}"     # 提交信息模板 {date} 会被替换为当前日期
exclude = [".DS_Store", "__pycache__", "*.pyc"]  # 全局排除规则

[[repos]]
name = "nvim"                         # 仓库名称
path = "~/Documents/Git/nvim/"        # Git 仓库本地路径
remotes = ["gitee", "github"]         # 远程仓库名列表

[[repos.files]]
source = "~/.config/nvim"             # 源文件/目录
dest = "."                            # 目标相对路径（相对于仓库根目录）

[[repos.files]]
source = "/path/to/single/file"       # 也支持单个文件
dest = "subdir"                       # 复制到仓库的子目录
```

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
| `gpa push <name>` | 推送指定仓库 |
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
