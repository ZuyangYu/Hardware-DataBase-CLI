"""Knowledge base commands — list, create, delete."""

import click
from ..client import HardwareDatabaseAPIError


@click.group("kb", help="Manage knowledge bases.")
def kb_group():
    pass


@kb_group.command("list", help="List accessible knowledge bases.")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output as JSON.")
@click.pass_context
def kb_list(ctx, json_mode):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    if json_mode:
        skin.json_mode = True
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
                skin.next_step("kb create <name>          创建一个新知识库")
                return
            skin.table("Knowledge Bases", ["Name", "Description", "Files"], [
                (r.get("name", ""), r.get("description", ""),
                 str(r.get("file_count", r.get("chunk_count", "") or "")))
                for r in rows
            ])
            first_kb = rows[0].get("name", "<name>")
            skin.next_step(
                f"file list --kb {first_kb}     查看该 KB 的文件",
                f"query ask --kb {first_kb} \"你的问题\"  基于该 KB 提问",
            )
    except HardwareDatabaseAPIError as e:
        skin.api_error("List KBs", e)
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
        else:
            skin.next_step(
                f"file upload --kb {name} <files...>  上传文件",
                f"perm grant --kb {name} --user <u> --permission read  授权访问",
            )
    except HardwareDatabaseAPIError as e:
        skin.api_error("Create KB", e)
        raise SystemExit(1)


@kb_group.command("delete", help="Delete a knowledge base.")
@click.argument("kb_name")
@click.option("-y", "--yes", is_flag=True, default=False, help="Skip confirmation.")
@click.pass_context
def kb_delete(ctx, kb_name, yes):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    if not yes and not click.confirm(
        f"Delete knowledge base '{kb_name}'? This cannot be undone."
    ):
        skin.info("Cancelled.")
        return
    try:
        client.delete_kb(kb_name)
        skin.success(f"Knowledge base [bold]{kb_name}[/bold] deleted.")
    except HardwareDatabaseAPIError as e:
        skin.api_error("Delete KB", e)
        raise SystemExit(1)