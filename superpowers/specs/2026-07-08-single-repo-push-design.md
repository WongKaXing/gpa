# GPA 单仓库推送功能设计

## 概述

为 GPA 添加单仓库推送功能，允许用户选择推送特定仓库，而非总是推送所有仓库。

## 功能需求

1. **交互菜单**：在现有菜单中添加 "推送指定仓库" 选项
2. **CLI 命令**：添加 `gpa push <name>` 命令
3. **仓库列表**：添加 `gpa list` 命令列出所有已配置仓库
4. **交互选择**：选择 "推送指定仓库" 后显示仓库列表供用户选择

## 设计方案

### 1. 交互菜单变更

**当前菜单**：
```
1. 执行 Git Push (同步并推送所有仓库)
2. 添加新的 Git 仓库
3. 管理已有仓库
4. 重新运行配置向导
5. 退出
```

**新菜单**：
```
1. 执行 Git Push (同步并推送所有仓库)
2. 推送指定仓库 (选择单个仓库推送)
3. 添加新的 Git 仓库
4. 管理已有仓库
5. 重新运行配置向导
6. 退出
```

### 2. CLI 命令

新增两个子命令：

```bash
# 列出所有已配置的仓库
gpa list

# 输出示例：
# 已配置的仓库：
#   1. nvim (~/Documents/Git/nvim)
#      远程: gitee, github
#   2. dotfiles (~/Documents/Git/dotfiles)
#      远程: github

# 推送指定仓库
gpa push <name>

# 示例：
gpa push nvim
```

### 3. 交互选择流程

当用户选择 "推送指定仓库" 时：

```
推送指定仓库:

  1. nvim
     ~/Documents/Git/nvim
     远程: gitee, github

  2. dotfiles
     ~/Documents/Git/dotfiles
     远程: github

  0. 返回

  输入仓库编号: 
```

- 显示仓库名称、路径、远程仓库
- 输入编号选择仓库
- 输入 0 返回主菜单
- 选择后立即执行推送

### 4. 错误处理

1. **仓库不存在**：
   - CLI: `gpa push xxx` → "未找到仓库 'xxx'，运行 `gpa list` 查看可用仓库"
   - 菜单: 输入无效编号 → "无效选项，请重新输入"

2. **无仓库配置**：
   - 菜单: "没有已配置的仓库，请先添加仓库" → 返回主菜单
   - CLI: "未找到配置文件或无仓库配置"

3. **推送失败**：
   - 复用现有错误处理逻辑，显示失败原因

## 实现计划

### 文件修改

1. **cli.py**
   - 添加 `_push_single_repo()` 函数处理交互式单仓库推送
   - 添加 `_list_repos()` 函数处理 `gpa list` 命令
   - 修改 `_interactive_menu()` 添加新菜单项
   - 修改 `_main()` 添加 `push` 和 `list` 子命令

2. **orchestrator.py**
   - 添加 `run_single()` 函数处理单仓库推送
   - 复用现有 `_process_repo()` 函数

### 代码结构

```python
# cli.py 新增函数

def _list_repos(config: Config) -> None:
    """列出所有已配置的仓库。"""
    print("\n已配置的仓库：")
    for i, repo in enumerate(config.repos, 1):
        print(f"  {i}. {repo.name}")
        print(f"     {repo.path}")
        if repo.remotes:
            print(f"     远程: {', '.join(repo.remotes)}")
    print()

def _push_single_repo(config: Config, config_path: Path, repo_name: str | None = None) -> bool:
    """推送单个仓库。如果未指定名称，显示交互选择。"""
    if not config.repos:
        print("  没有已配置的仓库，请先添加仓库。")
        return False
    
    if repo_name:
        # CLI 模式：按名称查找
        target = next((r for r in config.repos if r.name == repo_name), None)
        if not target:
            print(f"未找到仓库 '{repo_name}'，运行 `gpa list` 查看可用仓库")
            return False
        run_single(target, config_path)
        return True
    
    # 交互模式：显示列表选择
    print("\n推送指定仓库:\n")
    for i, repo in enumerate(config.repos, 1):
        remote_str = ", ".join(repo.remotes) if repo.remotes else "(无远程)"
        print(f"  {i}. {repo.name}")
        print(f"     {repo.path}")
        print(f"     远程: {remote_str}")
        print()
    print("  0. 返回")
    
    sel = _input_simple("\n  输入仓库编号: ")
    try:
        idx = int(sel) - 1
        if idx < 0 or idx >= len(config.repos):
            return False
    except (ValueError, IndexError):
        return False
    
    target = config.repos[idx]
    run_single(target, config_path)
    return True
```

```python
# orchestrator.py 新增函数

def run_single(repo: RepoConfig, config_path: str | Path) -> None:
    """运行单个仓库的同步和推送。"""
    config_dir = Path(config_path).resolve().parent
    print(f"\n开始推送 {repo.name}...")
    result = _process_repo(repo, config_dir)
    print_summary([result])
```

## 测试计划

1. **单元测试**：
   - 测试 `run_single()` 函数
   - 测试 `_list_repos()` 输出格式
   - 测试 `_push_single_repo()` 交互流程

2. **集成测试**：
   - 测试 CLI `gpa list` 命令
   - 测试 CLI `gpa push <name>` 命令
   - 测试菜单交互流程

## 文档更新

更新 README.md 添加新命令说明：
- `gpa list` 命令
- `gpa push <name>` 命令
- 交互菜单新选项

## 总结

此设计为 GPA 添加单仓库推送功能，支持：
- 交互菜单选择推送
- CLI 命令直接推送
- 仓库列表查看

实现简单，复用现有代码，保持一致性。