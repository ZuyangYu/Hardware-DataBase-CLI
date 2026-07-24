"""KB permission commands."""

import click
from ..client import HardwareDatabaseAPIError


@click.group("perm", help="Manage KB permissions.")
def perm_group():
    pass


@perm_group.command("list", help="List permissions for a KB.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.pass_context
def perm_list(ctx, kb):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_kb_permissions(kb)
        rows = data if isinstance(data, list) else data.get("permissions", data.get("data", []))
        if skin.json_mode:
            skin.json_out(rows)
        else:
            skin.table(f"Permissions for {kb}", ["User ID", "Username", "Permission"], [
                (r.get("user_id", ""), r.get("username", ""), r.get("permission", ""))
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@perm_group.command("grant", help="Grant a permission on a KB to a user.")
@click.option("--kb", required=True)
@click.option("--user-id", type=int, required=True)
@click.option("--permission", required=True, type=click.Choice(["read", "write", "admin"]))
@click.pass_context
def perm_grant(ctx, kb, user_id, permission):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        client.grant_kb_permission(kb, user_id, permission)
        skin.success(f"Granted {permission} on {kb} to user {user_id}.")
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@perm_group.command("assign-kb", help="Reassign a KB to another department (system_admin).")
@click.option("--kb", required=True)
@click.option("--dept-id", "department_id", type=int, required=True)
@click.pass_context
def perm_assign_kb(ctx, kb, department_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        client.assign_kb(kb, department_id)
        skin.success(f"KB {kb} reassigned to department {department_id}.")
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)