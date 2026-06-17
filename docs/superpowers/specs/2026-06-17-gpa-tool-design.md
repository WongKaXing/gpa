# GPA — Git Push All: Dotfiles Sync Tool

## Overview

A CLI tool (`gpa`) that syncs files into Git repositories and pushes to multiple remotes (Gitee, GitHub). Configured via an interactive setup wizard on first run, which generates a `gitpush.toml` config file for subsequent runs.

## Scope

Single-user CLI tool, pip-installable (`pip install .`). Interactive first-run setup, then driven by TOML config.

## First-Run Interactive Setup

`gpa` with no config present → starts wizard:

1. **Source path** — "Enter source directory to scan (e.g. `~/.config/`, or `None` to skip copy):"
   - If not None: scan the directory, list all subdirectories/files with numbered index
     ```
     Found in ~/.config/:
       1. nvim/
       2. kitty/
       3. yazi/
       4. starship.toml
     ```
   - "Select items to sync (comma-separated numbers, e.g. `1,3,4`, or `all`):"
   - Store selected items; non-selected items are excluded from sync
   - "Modify selection later? Current: nvim, yazi, starship.toml [y/n]:" → if y, allow re-select
2. **Upload path** — "Enter Git repo directory to sync into:"
   - Each selected item maps to a `[[repos.files]]` entry: `source = "<source_path>/nvim"`, `dest = "./"`
   - Wizard runs `git remote -v` in the repo to detect existing remotes
3. **Gitee remote** — auto-detected if `gitee` remote exists; otherwise prompt:
     "Gitee remote not found. Enter remote URL? (or `None` to skip):"
     → runs `git remote add gitee <url>` if URL provided
4. **GitHub remote** — auto-detected if `github` remote exists; otherwise prompt:
     "GitHub remote not found. Enter remote URL? (or `None` to skip):"
     → runs `git remote add github <url>` if URL provided
5. **Exclude patterns** — "Exclude glob patterns? (default: `.DS_Store`, `__pycache__`, `*.pyc`):"
6. **Commit template** — "Commit message template? (default: `update {date}`):"
7. **Add another repo?** — "Add another repo config? (y/n):" → loops back to step 1

Wizard generates `gitpush.toml` in current directory, then proceeds to run.

## Configuration Format (generated)

```toml
[defaults]
commit_template = "update {date}"
exclude = [".DS_Store", "__pycache__", "*.pyc"]

[[repos]]
name = "starship"
path = "~/Documents/Git/starship"
remotes = ["gitee", "github"]

[[repos.files]]
source = "~/.config/starship.toml"
dest = "."

[[repos.files]]
source = "~/.config/alacritty/"
dest = "./"
```

### Rules

- `defaults` keys inherited by each repo; repo-level overrides take precedence
- `exclude` is a list of glob patterns; matched files are **skipped** during copy (never copied, not copied-then-deleted)
- `source` can be a file or directory; directories recursively copied
- `dest` is relative to `path`; `~` expanded; relative paths resolve against TOML file directory
- `remotes` are git remote names; if user entered `None` for a platform, that remote is omitted
- If repo has no `[[repos.files]]` entries, file sync step is skipped entirely (user only wants git push)

## CLI Interface

```
gpa                        # run with ./gitpush.toml
gpa -c myconfig.toml       # use specific config
gpa init                   # re-run setup wizard to regenerate config
gpa --dry-run              # preview only, no changes
gpa -v                     # verbose
gpa -q                     # quiet, only errors
```

## Architecture

```
gitpush/
├── __init__.py
├── __main__.py             # python -m gitpush
├── cli.py                  # argparse, entry point → gpa command
├── wizard.py               # interactive setup, generates gitpush.toml
├── config.py               # TOML parse/validate, dataclass models
├── filesync.py             # file copy with glob-based exclusion
├── gitops.py               # git add, commit, push via subprocess
├── reporter.py             # terminal output, summary table, retry prompt
└── orchestrator.py         # ties modules together: run all repos, track results
```

### Module Responsibilities

| Module | Input | Output |
|--------|-------|--------|
| `cli.py` | `sys.argv` | parsed args, dispatches to wizard or orchestrator |
| `wizard.py` | user stdin responses | writes `gitpush.toml` |
| `config.py` | TOML file path | `Config(repos: list[RepoConfig])` dataclass |
| `filesync.py` | `RepoConfig` | `SyncResult(copied: int, skipped: list[str])` |
| `gitops.py` | repo path, remotes, commit_template | `GitResult(committed: bool, push_ok: list, push_fail: list)` |
| `orchestrator.py` | `Config` | `list[RepoResult]` |
| `reporter.py` | `list[RepoResult]` | formatted terminal output + retry prompt |

### Execution Flow (normal run)

```
cli.py parse args
  → if no config → wizard.py (generate gitpush.toml)
  → config.py load + validate gitpush.toml
  → orchestrator.py:
      for each repo:
        filesync.py: copy sources → dest, skipping exclude matches
        gitops.py:   git add -A
                     git diff --cached --quiet
                       → if changes: git commit -m <template>
                     for each remote: git push <remote>
      → reporter.py:
          print pretty per-repo summary with icons
          if any errors: prompt "Retry failed repos? [y/n]"
            → if y: re-run only failed repos, skip already-successful ones
```

## Error Handling & Retry

- **Source file/dir not found** → warn, skip that file entry, continue
- **Repo path not a git repo** → error, skip that repo, continue to next
- **No staged changes** → skip commit and push, report "no changes"
- **Push fails** (network/auth/not found) → record error, continue to next remote
- **Config parse error** → exit immediately
- All repo-level exceptions caught; never propagate

**Retry after errors:**
- Reporter prints which repos had errors and what failed
- Prompts: `Retry failed repos? [y/n]`
- If yes: orchestrator re-runs only the errored repos (successful ones skipped)
- Retry loop continues until all pass or user declines

## Reporter Output (pretty)

```
╭──────────────────────────────────────────────────────╮
│                    GPA Sync Result                    │
├────────────┬──────────┬───────────────────────────────┤
│ Repo       │ Status   │ Details                       │
├────────────┼──────────┼───────────────────────────────┤
│ starship   │ ✅ OK    │ committed, pushed → gitee, github│
│ alacritty  │ ✅ OK    │ committed, pushed → gitee, github│
│ kitty      │ ⬜ SKIP  │ no changes                     │
│ nvim       │ ❌ ERROR │ push failed: github (auth)      │
╰────────────┴──────────┴───────────────────────────────╯

 Errors in 1 repo(s). Retry failed repos? [y/n]:
```

## Package Entry Point

```toml
[project.scripts]
gpa = "gitpush.cli:main"
```

Install: `pip install .` or `uv tool install .`
Run: `gpa`

## Dependencies

- Python ≥ 3.12
- Standard library only: `tomllib`, `argparse`, `subprocess`, `shutil`, `pathlib`, `fnmatch`, `dataclasses`

## Testing Strategy

- **Unit tests** (pytest): config parsing, `exclude` glob matching, `{date}` template substitution, path expansion
- **Integration tests** (pytest + tmp_path): full flow with real git repo — init, add remote, sync, verify commits
- Git operations use real `git` CLI via subprocess (no mocking)
