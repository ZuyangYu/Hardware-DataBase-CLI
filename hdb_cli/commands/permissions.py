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
            if not rows:
                skin.next_step(
                    f"perm grant --kb {kb} --user <name> --permission read  为用户授权",
                )
    except HardwareDatabaseAPIError as e:
        skin.api_error("List permissions", e)
        raise SystemExit(1)


@perm_group.command("grant", help="Grant a permission on a KB to a user.")
@click.option("--kb", required=True)
@click.option("--user", "user_ref", required=True,
              help="Username or numeric user ID (either works).")
@click.option("--permission", required=True, type=click.Choice(["read", "write", "admin"]))
@click.pass_context
def perm_grant(ctx, kb, user_ref, permission):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        user_id = client.resolve_user_id(user_ref)
    except HardwareDatabaseAPIError as e:
        skin.api_error("Resolve user", e)
        raise SystemExit(1)
    try:
        client.grant_kb_permission(kb, user_id, permission)
        skin.success(f"Granted [bold]{permission}[/bold] on {kb} to user {user_ref} (id={user_id}).")
    except HardwareDatabaseAPIError as e:
        skin.api_error("Grant permission", e)
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
        skin.api_error("Reassign KB", e)
        raise SystemExit(1)