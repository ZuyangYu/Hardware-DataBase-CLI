"""REPL engine — interactive command loop using prompt_toolkit."""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

import click

from .client import HardwareDatabaseAPIError
from .skin import ConsoleSkin


HISTORY_DIR = Path.home() / ".config" / "hdb-cli"
HISTORY_FILE = HISTORY_DIR / "history"


class ReplEngine:
    """Interactive REPL for the HDB CLI.

    Delegates all command parsing and execution to the Click root group.
    """

    def __init__(self, cli_func, ctx_obj: dict, skin: ConsoleSkin):
        self.cli_func = cli_func
        self.ctx_obj = ctx_obj
        self.skin = skin
        self._prompt_session = None
        # KB context: when set, commands that accept --kb but omit it inherit this
        self._current_kb: str | None = None

    def _get_prompt_session(self):
        if self._prompt_session is not None:
            return self._prompt_session
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import FileHistory
            from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
            from prompt_toolkit.styles import Style

            style = Style.from_dict({
                "prompt": "ansicyan bold",
            })
            self._prompt_session = PromptSession(
                history=FileHistory(str(HISTORY_FILE)),
                auto_suggest=AutoSuggestFromHistory(),
                style=style,
            )
        except ImportError:
            self._prompt_session = None
        return self._prompt_session

    def _prompt_str(self) -> str:
        """Build the REPL prompt, reflecting current KB context if set."""
        if self._current_kb:
            return f"hdb({self._current_kb})> "
        return "hdb> "

    def run(self) -> None:
        """Enter the REPL loop."""
        self.skin.banner()
        self._print_startup_hint()
        session = self._get_prompt_session()
        if session is not None:
            self._run_prompt_toolkit(session)
        else:
            self._run_fallback()

    def _print_startup_hint(self) -> None:
        session = self.ctx_obj.get("session")
        if session and session.token:
            self.skin.info(
                f"Logged in as [bold]{session.username}[/bold] ({session.role or '?'})"
            )
        else:
            self.skin.info("Not logged in — auth commands will prompt for login.")
        self.skin.hint("Type [bold]help[/bold] for commands, [bold]quit[/bold] to exit.\n")

    def _run_prompt_toolkit(self, session) -> None:
        while True:
            try:
                line = session.prompt(message=[("class:prompt", self._prompt_str())])
            except (KeyboardInterrupt, EOFError):
                print()
                break
            if not self._dispatch(line):
                break
        self.skin.goodbye()

    def _run_fallback(self) -> None:
        while True:
            try:
                line = input(self._prompt_str())
            except (KeyboardInterrupt, EOFError):
                print()
                break
            if not self._dispatch(line):
                break
        self.skin.goodbye()

    def _handle_repl_special(self, line: str) -> bool | None:
        """Return True if handled, False if should quit, None if not special."""
        stripped = line.strip()
        if not stripped:
            return True
        if stripped in ("quit", "exit", "q"):
            return False
        if stripped in ("help", "h", "?"):
            self.skin.console.print(REPL_HELP)
            return True
        # use <kb> — set KB context
        if stripped.startswith("use "):
            kb = stripped[4:].strip()
            if kb:
                self._current_kb = kb
                self.skin.success(f"Now using KB: [bold]{kb}[/bold]")
                self.skin.hint("Commands that accept --kb inherit it automatically.")
            else:
                self.skin.error("Usage: use <kb-name>")
            return True
        if stripped == "unuse":
            if self._current_kb:
                self.skin.info(f"Cleared KB context: {self._current_kb}")
                self._current_kb = None
            else:
                self.skin.info("No KB context set.")
            return True
        return None

    def _dispatch(self, line: str) -> bool:
        """Dispatch a line through Click. Returns False to exit REPL."""
        result = self._handle_repl_special(line)
        if result is not None:
            return result
        try:
            args = shlex.split(line, comments=True)
        except ValueError as e:
            self.skin.error(f"Parse error: {e}")
            return True
        if not args:
            return True
        # Inject --kb from context if command accepts it and user didn't provide
        args = self._inject_kb_context(args)
        try:
            self.cli_func(args=args, obj=self.ctx_obj, standalone_mode=False)
        except SystemExit:
            # Click raises SystemExit for --help, errors, etc. — continue REPL.
            pass
        except click.ClickException as e:
            self.skin.error(f"Error: {e.format_message()}")
        except HardwareDatabaseAPIError as e:
            self.skin.error(f"API error: {e.message}", hint=e.hint)
        except Exception as e:
            self.skin.error(f"Unexpected error: {e}")
        return True

    # Commands that accept a --kb option. Used by `use <kb>` context injection.
    _KB_COMMANDS = {
        ("file", "list"), ("file", "upload"), ("file", "delete"), ("file", "chunks"),
        ("query", "ask"),
        ("perm", "list"), ("perm", "grant"), ("perm", "assign-kb"),
        ("task", "list"), ("task", "clear-finished"), ("task", "delete"),
        ("task", "pause"), ("task", "resume"),
        ("conv", "list"), ("conv", "create"),
    }

    def _inject_kb_context(self, args: list[str]) -> list[str]:
        """If a KB context is set via `use`, inject --kb into KB-aware commands."""
        if not self._current_kb or len(args) < 2:
            return args
        cmd_key = (args[0], args[1])
        if cmd_key not in self._KB_COMMANDS:
            return args
        # Already has --kb somewhere → leave alone
        if any(a == "--kb" or a.startswith("--kb=") for a in args):
            return args
        return args[:2] + ["--kb", self._current_kb] + args[2:]


# Lazy imports for dispatch

REPL_HELP = """
[bold]Commands[/bold] — run any CLI command directly:
  [bold]server health[/bold]          Server health check
  [bold]auth login --user <u>[/bold]  Log in
  [bold]auth logout[/bold]            Log out
  [bold]auth whoami[/bold]            Show current user
  [bold]auth status[/bold]            Show local session
  [bold]doctor[/bold]                 Full diagnostic report
  [bold]kb list[/bold]                List knowledge bases
  [bold]kb create <name>[/bold]       Create a KB
  [bold]kb delete <name>[/bold]       Delete a KB
  [bold]file list --kb <n>[/bold]     List files in a KB
  [bold]file upload --kb <n> <f>[/bold] Upload files
  [bold]file delete --kb <n> --name <f>[/bold] Delete a file
  [bold]query ask --kb <n> <q>[/bold] Ask a question (streaming)
  [bold]user list[/bold]              List users
  [bold]dept list[/bold]              List departments
  [bold]perm list --kb <n>[/bold]     List KB permissions
  [bold]perm grant --kb <n> --user <name> --permission <p>[/bold]  Grant permission
  [bold]task list --kb <n>[/bold]     List parse tasks
  [bold]conv list[/bold]              List conversations
  [bold]gov stats[/bold]              Governance stats
  [bold]log audit[/bold]              Audit log
  [bold]config get[/bold]             Server config

[bold]REPL Commands[/bold]
  [bold]use <kb>[/bold]         Set KB context (auto-inject --kb to subcommands)
  [bold]unuse[/bold]             Clear KB context
  [bold]help[/bold] / [bold]h[/bold] / [bold]?[/bold]  Show this help
  [bold]quit[/bold] / [bold]exit[/bold] / [bold]q[/bold]  Exit REPL
  Ctrl+D / Ctrl+C                     Exit REPL

[bold]Global flags[/bold] (available on every command):
  --json         JSON output mode
  --api-url URL  Override API server
  --token TOK    Override bearer token
  -v/--verbose   Show HTTP request/response details
"""