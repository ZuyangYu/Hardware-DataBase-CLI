"""User management commands."""

import click
from ..client import HardwareDatabaseAPIError


@click.group("user", help="User management (admin-only).")
def user_group():
    pass


@user_group.command("list", help="List all users.")
@click.pass_context
def user_list(ctx):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_users()
        rows = data if isinstance(data, list) else data.get("users", data.get("data", []))
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No users.")
                return
            skin.table("Users", ["ID", "Username", "Role", "Dept", "Active"], [
                (
                    r.get("id", ""),
                    r.get("username", ""),
                    r.get("role", ""),
                    r.get("department_id", r.get("department", "")),
                    "yes" if r.get("active", True) else "no",
                )
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@user_group.command("create", help="Create a new user.")
@click.option("--username", "-u", required=True)
@click.option("--password", "-p", default=None)
@click.option("--role", required=True, type=click.Choice(["user", "dept_admin", "system_admin"]))
@click.option("--dept-id", "department_id", type=int, default=None)
@click.pass_context
def user_create(ctx, username, password, role, department_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    if not password:
        password = click.prompt("Password for new user", hide_input=True, confirmation_prompt=True)
    try:
        resp = client.create_user(username, password, role, department_id)
        skin.success(f"User [bold]{username}[/bold] created.")
        if skin.json_mode:
            skin.json_out(resp)
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@user_group.command("set-active", help="Activate or deactivate a user.")
@click.argument("user_id", type=int)
@click.option("--active/--inactive", default=True)
@click.pass_context
def user_set_active(ctx, user_id, active):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        client.set_user_active(user_id, active)
        skin.success(f"User {user_id} set to {'active' if active else 'inactive'}.")
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@user_group.command("reset-password", help="Reset a user's password.")
@click.argument("user_id", type=int)
@click.option("--password", "-p", default=None)
@click.pass_context
def user_reset_password(ctx, user_id, password):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    if not password:
        password = click.prompt("New password", hide_input=True, confirmation_prompt=True)
    try:
        client.reset_user_password(user_id, password)
        skin.success(f"Password reset for user {user_id}.")
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)