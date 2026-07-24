"""Terminal output helpers built on Rich.

Provides ConsoleSkin with uniform methods for success/error/table/json
rendering. Global --json flag switches all output to structured JSON.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Iterable

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box


BANNER = r"""[bold cyan]
 _   _ ____  ____     ____ _     ___
| | | |  _ \| __ )   / ___| |   |_ _|
| |_| | | | |  _ \  | |   | |    | |
|  _  | |_| | |_) | | |___| |___ | |
|_| |_|____/|____/   \____|_____|___|
[/bold cyan]
[dim]Hardware DataBase CLI · type [b]help[/b] for commands, [b]quit[/b] to exit[/dim]
"""


class ConsoleSkin:
    """Formatted terminal output. Honors ``json_mode`` for structured output."""

    def __init__(self, json_mode: bool = False):
        self.json_mode = json_mode
        self.console = Console(highlight=False)
        self.err_console = Console(stderr=True, highlight=False)

    # ── plain messages ───────────────────────────────────────────────

    def success(self, msg: str) -> None:
        if self.json_mode:
            self._json({"status": "ok", "message": msg})
        else:
            self.console.print(f"[green]✓[/green] {msg}")

    def error(self, msg: str) -> None:
        if self.json_mode:
            self._json({"status": "error", "message": msg}, err=True)
        else:
            self.err_console.print(f"[red]✗[/red] {msg}")

    def warning(self, msg: str) -> None:
        if self.json_mode:
            return
        self.console.print(f"[yellow]![/yellow] {msg}")

    def info(self, msg: str) -> None:
        if self.json_mode:
            return
        self.console.print(f"[cyan]·[/cyan] {msg}")

    def section(self, msg: str) -> None:
        if self.json_mode:
            return
        self.console.print(f"\n[bold]{msg}[/bold]")

    def hint(self, msg: str) -> None:
        if self.json_mode:
            return
        self.console.print(f"[dim]{msg}[/dim]")

    def banner(self) -> None:
        if self.json_mode:
            return
        self.console.print(BANNER)

    def goodbye(self) -> None:
        if self.json_mode:
            return
        self.console.print("\n[cyan]Goodbye![/cyan]")

    # ── structured output ───────────────────────────────────────────

    def table(self, title: str | None, headers: list[str], rows: Iterable[list[Any]]) -> None:
        rows = list(rows)
        if self.json_mode:
            data = [dict(zip(headers, r)) for r in rows]
            self._json({"title": title, "rows": data} if title else data)
            return
        tbl = Table(title=title, box=box.ROUNDED, show_lines=False)
        for h in headers:
            tbl.add_column(h)
        for row in rows:
            tbl.add_row(*[str(c) if c is not None else "" for c in row])
        self.console.print(tbl)

    def json_out(self, obj: Any) -> None:
        """Always emit JSON (even outside --json mode; used by --json commands)."""
        self._json(obj)

    def display(self, obj: Any) -> None:
        """Print object: JSON in json_mode, else rich pretty print."""
        if self.json_mode:
            self._json(obj)
        else:
            if isinstance(obj, (dict, list)):
                self.console.print_json(json.dumps(obj, ensure_ascii=False, default=str))
            else:
                self.console.print(str(obj))

    def key_value(self, title: str | None, mapping: dict) -> None:
        if self.json_mode:
            self._json(mapping)
            return
        panel_body = "\n".join(
            f"[bold]{k}[/bold]: {v}" for k, v in mapping.items()
        )
        self.console.print(Panel(panel_body, title=title or "", box=box.ROUNDED))

    # ── internal ─────────────────────────────────────────────────────

    def _json(self, obj: Any, err: bool = False) -> None:
        text = json.dumps(obj, indent=2, ensure_ascii=False, default=str)
        (self.err_console if err else self.console).print(text)
