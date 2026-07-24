"""Department commands."""

import click
from ..client import HardwareDatabaseAPIError


@click.group("dept", help="Department management.")
def dept_group():
    pass


@dept_group.command("list", help="List departments.")
@click.pass_context
def dept_list(ctx):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_departments()
        rows = data if isinstance(data, list) else data.get("departments", data.get("data", []))
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No departments.")
                return
            skin.table("Departments", ["ID", "Name", "Description"], [
                (r.get("id", ""), r.get("name", ""), r.get("description", ""))
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@dept_group.command("create", help="Create a department (system_admin only).")
@click.argument("name")
@click.option("--description", "-d", default=None)
@click.pass_context
def dept_create(ctx, name, description):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        resp = client.create_department(name, description)
        skin.success(f"Department [bold]{name}[/bold] created.")
        if skin.json_mode:
            skin.json_out(resp)
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@dept_group.command("delete", help="Delete a department (system_admin only).")
@click.argument("department_id", type=int)
@click.pass_context
def dept_delete(ctx, department_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    if not click.confirm(f"Delete department {department_id}?"):
        skin.info("Cancelled.")
        return
    try:
        client.delete_department(department_id)
        skin.success(f"Department {department_id} deleted.")
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)