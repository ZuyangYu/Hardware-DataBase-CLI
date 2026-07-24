"""Knowledge base commands — list, create, delete."""

import click
from ..client import HardwareDatabaseAPIError


@click.group("kb", help="Manage knowledge bases.")
def kb_group():
    pass


@kb_group.command("list", help="List accessible knowledge bases.")
@click.pass_context
def kb_list(ctx):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_kbs()
        # Tolerate list / wrapped / data-wrapped shapes
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get("kbs", data.get("data", []))
        else:
            rows = []
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No knowledge bases found.")
                return
            skin.table("Knowledge Bases", ["Name", "Description", "Files"], [
                (r.get("name", ""), r.get("description", ""), str(r.get("file_count", r.get("chunk_count", "?"))))
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed to list KBs: {e.message}")
        raise SystemExit(1)


@kb_group.command("create", help="Create a new knowledge base.")
@click.argument("name")
@click.option("--description", "-d", default=None, help="KB description")
@click.pass_context
def kb_create(ctx, name, description):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        resp = client.create_kb(name, description)
        skin.success(f"Knowledge base [bold]{name}[/bold] created.")
        if skin.json_mode:
            skin.json_out(resp)
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed to create KB: {e.message}")
        raise SystemExit(1)


@kb_group.command("delete", help="Delete a knowledge base.")
@click.argument("kb_name")
@click.pass_context
def kb_delete(ctx, kb_name):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    confirm = click.confirm(f"Delete knowledge base '{kb_name}'? This cannot be undone.")
    if not confirm:
        skin.info("Cancelled.")
        return
    try:
        client.delete_kb(kb_name)
        skin.success(f"Knowledge base [bold]{kb_name}[/bold] deleted.")
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed to delete KB: {e.message}")
        raise SystemExit(1)