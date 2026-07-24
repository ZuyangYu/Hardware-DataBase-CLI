"""Auth commands — login, logout, whoami, status."""

import click
from .. import config as cfg
from ..client import HardwareDatabaseAPIError


@click.group("auth", help="Authentication & session management.")
def auth_group():
    pass


@auth_group.command("login", help="Log in with username/password.")
@click.option("--user", "-u", required=True, help="Username")
@click.option("--password", "-p", default=None, help="Password (prompted if omitted)")
@click.pass_context
def auth_login(ctx, user, password):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    if not password:
        password = click.prompt("Password", hide_input=True)
    try:
        resp = client.login(user, password)
        # Extract user info from server response
        token = resp.get("token", "")
        user_info = resp.get("user", resp)
        username = user_info.get("username", user)
        role = user_info.get("role", "")
        department_id = user_info.get("department_id")
        session = cfg.Session(
            api_url=client.base_url,
            token=token,
            username=username,
            role=role,
            department_id=str(department_id) if department_id is not None else None,
        )
        cfg.save(session)
        skin.success(f"Logged in as [bold]{username}[/bold] ({role})")
    except HardwareDatabaseAPIError as e:
        skin.error(f"Login failed: {e.message}")
        raise SystemExit(1)


@auth_group.command("logout", help="Log out and clear saved session.")
@click.pass_context
def auth_logout(ctx):
    skin = ctx.obj["skin"]
    was_present = cfg.clear()
    if was_present:
        skin.success("Logged out. Session file cleared.")
    else:
        skin.info("No session to clear.")
    # Clear client token
    ctx.obj["client"].set_token("")
    ctx.obj["session"] = None


@auth_group.command("whoami", help="Show current user info (from server).")
@click.pass_context
def auth_whoami(ctx):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.whoami()
        # Handle both wrapped and flat responses
        user = data.get("user", data) if isinstance(data, dict) else data
        if skin.json_mode:
            skin.json_out(user)
        else:
            if isinstance(user, dict):
                skin.key_value("User Info", user)
            else:
                skin.display(user)
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed to get user info: {e.message}")
        raise SystemExit(1)


@auth_group.command("status", help="Show local session status (no network).")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output as JSON.")
@click.pass_context
def auth_status(ctx, json_mode):
    skin = ctx.obj["skin"]
    # If --json was passed to this command, override skin's json_mode
    if json_mode:
        skin.json_mode = True
    session = ctx.obj.get("session")
    if session is None:
        if skin.json_mode:
            skin.json_out({"logged_in": False})
        else:
            skin.info("Not logged in. Run [bold]auth login[/bold] first.")
        return
    if skin.json_mode:
        d = session.to_dict()
        if d.get("token"):
            d["token"] = d["token"][:8] + "..."
        skin.json_out(d)
    else:
        skin.key_value("Local Session", {
            "API URL": session.api_url,
            "Username": session.username or "?",
            "Role": session.role or "?",
            "Token": (session.token[:8] + "...") if session.token else "None",
        })