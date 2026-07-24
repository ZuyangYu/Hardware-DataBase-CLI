# Hardware DataBase CLI

Standalone CLI client for the [Hardware DataBase](https://github.com/ZuyangYu/Hardware-DataBase-dev) HTTP API — an IT hardware design knowledge management platform.

Covers all ~44 API endpoints with built-in interactive REPL, streaming query support, and rich terminal output.

## Install

```bash
pip install -e .
# or from the repo
pip install -e ".[dev]"
```

## Quick Start

```bash
# Set the API server address (default: http://127.0.0.1:8000)
export HDB_API_URL=http://your-server:8000

# First-time login
hdb auth login --user admin

# Check server health
hdb server health

# List knowledge bases
hdb kb list

# Upload a file
hdb file upload --kb my-kb ./document.pdf

# Ask a question (streaming)
hdb query ask --kb my-kb "What is the max clock frequency?"

# Drop into interactive REPL
hdb
```

## Commands

| Group | Commands | Requires |
|-------|----------|----------|
| `server` | `health` | — |
| `auth` | `login`, `logout`, `whoami`, `status` | — |
| `kb` | `list`, `create`, `delete` | varies |
| `file` | `list`, `upload`, `delete`, `chunks` | varies |
| `query` | `ask` (SSE streaming) | auth |
| `user` | `list`, `create`, `set-active`, `reset-password` | dept_admin |
| `dept` | `list`, `create`, `delete` | varies |
| `perm` | `list`, `grant`, `assign-kb` | varies |
| `task` | `list`, `clear-finished`, `delete`, `pause`, `resume` | auth |
| `conv` | `list`, `create`, `delete`, `clear`, `messages`, `send` | auth |
| `gov` | `stats`, `kb-summaries` | auth |
| `config` | `get`, `set`, `ragflow-health` | varies |
| `log` | `audit`, `audit-stats`, `audit-actions`, `query-traces`, `query-stats`, `trace-evidence` | admin |
| `doctor` | (default), `config` | — |
| `completion` | `bash`, `zsh`, `fish` | — |
| `version` | — | — |

## Global Options

```
--api-url URL    API server URL (env: HDB_API_URL, default: http://127.0.0.1:8000)
--token TOKEN    Bearer token (env: HDB_TOKEN)
--json           Output as JSON instead of formatted tables
-v/--verbose     Print HTTP method/URL/status for every request
--help           Show help
```

## Diagnostics & Troubleshooting

When something doesn't work, run:

```bash
hdb doctor              # Full diagnostic report
hdb doctor config       # Show resolved configuration
hdb -v <any-command>    # Print HTTP request/response details
```

Common issues:

- **`Login failed: HTTP 500`** — the *server* is broken (not your credentials). Run `hdb doctor` to confirm.
- **`Query failed: read permission required`** — you lack access to that KB. Run `hdb perm list --kb <name>` and ask an admin to grant permission.
- **`No such option: --json` on subcommands** — most output commands accept `--json` locally now (`hdb kb list --json`, `hdb auth status --json`, etc.). If a command doesn't, put the flag before the subcommand: `hdb --json <cmd>`.

## Shell Completion

Enable tab completion for command names, subcommands, and option names:

```bash
# Bash
eval "$(_HDB_COMPLETE=bash_source hdb)"
# Zsh
eval "$(_HDB_COMPLETE=zsh_source hdb)"
# Fish
_HDB_COMPLETE=fish_source hdb | source
```

Run `hdb completion <shell>` to print the exact command.

## REPL

Run `hdb` without arguments to enter the interactive REPL:

```
hdb> server health
  Healthy — hw-db v0.1.0

hdb> kb list
  Name        Description           Files
  circuits    Circuit designs       12
  datasheets  Device datasheets     45

hdb> use circuits                   # Set KB context
  Now using KB: circuits

hdb(circuits)> file list            # --kb auto-injected
hdb(circuits)> query ask "What is C1101?"
hdb(circuits)> unuse                # Clear context

hdb> quit
Goodbye!
```

Features: command history, auto-suggest, KB context via `use`/`unuse`, falls back to plain `input()` if prompt_toolkit is missing.

## Destructive Commands

Commands that delete data prompt for confirmation. Pass `-y/--yes` to skip:

```bash
hdb kb delete my-kb --yes
hdb dept delete 42 --yes
hdb file delete --kb my-kb --name foo.pdf --yes
```

## API Endpoints Covered

The CLI wraps all ~44 endpoints of the Hardware DataBase REST API:

- **Health** — server ping
- **Auth** — login/logout/whoami (bearer token)
- **Users** — CRUD + password reset (admin)
- **Departments** — list/create/delete
- **Knowledge Bases** — list/create/delete
- **KB Files** — list/upload/delete/file chunks
- **KB Permissions** — list/grant/reassign
- **Parse Tasks** — list/clear/delete/pause/resume
- **Query** — streaming SSE chat
- **Conversations** — full session management
- **Governance** — stats + KB summaries
- **Config** — server config + RAGFlow health
- **Logs** — audit + query traces

## Configuration

Session (token + role + username) is persisted to `~/.config/hdb-cli/session.json` (mode 0600). Override the config directory:

```bash
export HDB_CONFIG_DIR=/custom/path
```

## License

MIT