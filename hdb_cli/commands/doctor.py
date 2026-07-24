"""Diagnostic command — hdb doctor."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from .. import config as cfg
from ..client import HardwareDatabaseAPIError


@click.group("doctor", help="System diagnostics & troubleshooting.", invoke_without_command=True)
@click.pass_context
def doctor_group(ctx):
    """Run a full diagnostic check.

    Tests: config file, API connectivity, auth status, session validity.
    """
    if ctx.invoked_subcommand is not None:
        return
    skin = ctx.obj["skin"]
    client = ctx.obj["client"]
    session = ctx.obj.get("session")
    api_url = ctx.obj.get("api_url", "?")

    skin.section("Hardware DataBase CLI — Diagnostic Report")
    print()

    # 1. Config file
    skin.info(f"Config dir: [bold]{cfg.CONFIG_DIR}[/bold]")
    if cfg.TOKEN_FILE.exists():
        skin.success(f"Session file present ({cfg.TOKEN_FILE})")
        try:
            sz = cfg.TOKEN_FILE.stat().st_size
            mode = oct(cfg.TOKEN_FILE.stat().st_mode)[-3:]
            skin.hint(f"  Size: {sz} bytes, Permissions: {mode}")
        except OSError:
            pass
    else:
        skin.warning("No session file — run `hdb auth login` to save one.")

    # 2. API URL
    skin.info(f"API URL: [bold]{api_url}[/bold]")
    env_url = os.environ.get("HDB_API_URL")
    if env_url and env_url != api_url:
        skin.hint(f"  (HDB_API_URL env: {env_url})")

    # 3. Connectivity
    try:
        data = client.health()
        ver = data.get("version", "?")
        skin.success(f"Server reachable (v{ver})")
    except HardwareDatabaseAPIError as e:
        skin.api_error("Connectivity check", e)
        if e.status_code in (0,):
            skin.next_step(
                "检查后端是否在运行: 确认 backend 进程是否存在",
                "或使用 --api-url 指定其他地址",
            )
        print()
        skin.hint("Run `hdb doctor --api-url <url>` to test a different URL.")
        return

    # 4. Auth
    if session and session.token:
        token_preview = session.token[:12] + "…"
        skin.info(f"Token: {token_preview}")
        try:
            who = client.whoami()
            user = who if isinstance(who, str) else who.get("username", "?")
            role = who.get("role", "?") if isinstance(who, dict) else "?"
            skin.success(f"Authenticated as [bold]{user}[/bold] ({role})")
        except HardwareDatabaseAPIError as e:
            skin.api_error("Auth check", e)
            skin.next_step("运行 `hdb auth login` 重新登录")
    else:
        skin.warning("No token — some commands will prompt for login.")

    # 5. Environment
    print()
    skin.info("Environment:")
    skin.hint(f"  Python: {sys.version.split()[0]}")
    skin.hint(f"  Config dir: {cfg.CONFIG_DIR}")
    skin.hint(f"  HDB_CONFIG_DIR: {os.environ.get('HDB_CONFIG_DIR', '(not set)')}")
    skin.hint(f"  HDB_API_URL: {os.environ.get('HDB_API_URL', '(not set)')}")

    print()
    skin.success("Diagnostic complete.")


@doctor_group.command("config", help="Show resolved config values.")
@click.pass_context
def doctor_config(ctx):
    """Show the resolved configuration (URL, token, session file)."""
    skin = ctx.obj["skin"]
    session = ctx.obj.get("session")
    api_url = ctx.obj.get("api_url", "?")

    info = {
        "api_url": api_url,
        "has_token": bool(session and session.token),
        "username": session.username if session else None,
        "role": session.role if session else None,
        "config_dir": str(cfg.CONFIG_DIR),
        "session_file": str(cfg.TOKEN_FILE) if cfg.TOKEN_FILE.exists() else None,
        "env_hdb_api_url": os.environ.get("HDB_API_URL"),
        "env_hdb_token": os.environ.get("HDB_TOKEN") is not None,
    }
    if skin.json_mode:
        skin.json_out(info)
    else:
        skin.key_value("Resolved Configuration", info)