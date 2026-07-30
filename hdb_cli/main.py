"""Main entry — Click root group + global options + REPL bootstrap.

Auth flow:
  1. Load ~/.config/hdb-cli/session.json if present.
  2. Resolve api_url and token in the order: CLI flag > env > saved session > default.
  3. If an authenticated subcommand runs without a token, interactively
     prompt for username/password, POST /login, save the session, continue.
  4. Bare ``hdb`` with no subcommand opens the interactive REPL.
"""

from __future__ import annotations

import os
import sys

import click

from . import config as cfg
from .client import HardwareDatabaseClient, HardwareDatabaseAPIError
from .skin import ConsoleSkin
from .repl import ReplEngine
from .commands.server import server_group
from .commands.auth import auth_group
from .commands.kbs import kb_group
from .commands.files import file_group
from .commands.query import query_group
from .commands.users import user_group
from .commands.departments import dept_group
from .commands.permissions import perm_group
from .commands.parse_tasks import task_group
from .commands.conversations import conv_group
from .commands.governance import gov_group
from .commands.config_cmd import config_group
from .commands.logs import log_group
from .commands.doctor import doctor_group
from .commands.misc import completion_cmd, version_cmd
from .commands.assets import asset_group as assets_group
from .commands.structured import structured_group
from .commands.evaluation import eval_group as evaluation_group


DEFAULT_URL = "http://127.0.0.1:8001"

# Groups that do NOT require a token. Everything else prompts login if
# no session is on disk.
_NO_AUTH_GROUPS = {"server", "auth", "doctor", "completion", "version"}


def _needs_auth(invoked: str | None, argv: list[str]) -> bool:
    if invoked is None:
        # REPL — auth is lazy (commands prompt inside)
        return False
    if any(a in ("--help", "-h") for a in argv):
        return False
    # Also check via Click's get_current_context to catch test-runners where
    # sys.argv isn't the CLI invocation.
    try:
        ctx = click.get_current_context()
        if any("--help" in a or a == "-h" for a in ctx.args):
            return False
    except RuntimeError:
        pass  # No click context yet — fall through
    if invoked not in _NO_AUTH_GROUPS:
        return True
    if invoked == "auth":
        try:
            i = argv.index("auth")
            sub = argv[i + 1] if i + 1 < len(argv) else None
        except ValueError:
            sub = None
        return sub == "whoami"
    return False


def _interactive_login(client: HardwareDatabaseClient, skin: ConsoleSkin, api_url: str):
    """Prompt user/pass, log in, save session. Returns Session or raises."""
    skin.section("Login required")
    skin.info(f"API: {api_url}")
    username = click.prompt("Username", type=str)
    password = click.prompt("Password", hide_input=True)
    resp = client.login(username, password)
    user_info = resp.get("user", resp) if isinstance(resp, dict) else {}
    token = resp.get("token", "") if isinstance(resp, dict) else ""
    session = cfg.Session(
        api_url=api_url,
        token=token,
        username=user_info.get("username", username),
        role=user_info.get("role", ""),
    )
    cfg.save_session(session.api_url, session.token, session.username or username, session.role or "")
    return session


@click.group(invoke_without_command=True, help="Standalone CLI for the Hardware DataBase API.")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output as JSON.")
@click.option("--api-url", default=None, help="API server URL (env: HDB_API_URL).")
@click.option("--token", default=None, help="Bearer token (env: HDB_TOKEN).")
@click.option("-v", "--verbose", is_flag=True, default=False,
              help="Print HTTP method/URL/status for every request.")
@click.version_option(package_name="hardware-database-cli")
@click.pass_context
def cli(ctx, json_mode, api_url, token, verbose):
    ctx.ensure_object(dict)
    skin = ConsoleSkin(json_mode=json_mode)

    saved = cfg.load_session(cli_url=api_url, cli_token=token)
    resolved_url = saved.api_url or DEFAULT_URL
    resolved_token = saved.token
    role = saved.role
    username = saved.username

    # Rebuild a Session for downstream code (only if we have a token)
    session_obj = None
    if resolved_token:
        session_obj = cfg.Session(
            api_url=resolved_url,
            token=resolved_token,
            username=username,
            role=role,
        )

    client = HardwareDatabaseClient(base_url=resolved_url, token=resolved_token)
    if verbose:
        client.set_verbose_logger(lambda msg: skin.console.print(f"[dim]{msg}[/dim]"))

    ctx.obj.update({
        "json": json_mode,
        "verbose": verbose,
        "api_url": resolved_url,
        "client": client,
        "skin": skin,
        "session": session_obj,
    })

    # Force interactive login if the invoked group needs auth and no token
    if _needs_auth(ctx.invoked_subcommand, sys.argv) and not resolved_token:
        try:
            new_session = _interactive_login(client, skin, resolved_url)
        except HardwareDatabaseAPIError as e:
            skin.error(f"Login failed: {e.message}")
            raise SystemExit(1)
        except click.Abort:
            skin.error("Login cancelled.")
            raise SystemExit(1)
        ctx.obj["session"] = new_session
        skin.success(f"Logged in as [bold]{new_session.username}[/bold] ({new_session.role})")
        skin.hint(f"Session saved to {cfg.TOKEN_FILE}")
        print()

    # No subcommand → REPL
    if ctx.invoked_subcommand is None:
        engine = ReplEngine(cli_func=cli.main, ctx_obj=ctx.obj, skin=skin)
        engine.run()


# Register all command groups
for _grp in (
    server_group, auth_group, kb_group, file_group, query_group,
    user_group, dept_group, perm_group, task_group, conv_group,
    gov_group, config_group, log_group, doctor_group,
    assets_group, structured_group, evaluation_group,
):
    cli.add_command(_grp)

# Standalone (leaf) commands
cli.add_command(completion_cmd)
cli.add_command(version_cmd)


def main():
    """Entry point for the ``hdb`` console script."""
    cli(auto_envvar_prefix="HDB")


if __name__ == "__main__":
    main()
