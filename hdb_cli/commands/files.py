"""File commands — list, upload, delete, chunks."""

import os

import click
from ..client import HardwareDatabaseAPIError


@click.group("file", help="Manage files inside knowledge bases.")
def file_group():
    pass


@file_group.command("list", help="List files in a knowledge base.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.pass_context
def file_list(ctx, kb):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_files(kb)
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get("files", data.get("data", []))
        else:
            rows = []
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info(f"No files in KB [bold]{kb}[/bold].")
                return
            skin.table(f"Files in {kb}", ["Name", "Type", "Size", "Status"], [
                (
                    r.get("name", r.get("filename", "")),
                    r.get("type", r.get("mime_type", "")),
                    str(r.get("size", "")),
                    r.get("status", r.get("parse_status", "")),
                )
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.api_error("List files", e)
        raise SystemExit(1)


@file_group.command("upload", help="Upload one or more files to a KB.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--group", "source_group", default=None, help="Optional source_group tag")
@click.argument("files", nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def file_upload(ctx, kb, source_group, files):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    # Client-side role guard (server also enforces)
    session = ctx.obj.get("session")
    if session and session.role not in ("dept_admin", "system_admin"):
        skin.error(
            f"权限不足: 需要 dept_admin 或 system_admin, 当前身份 {session.role or '未登录'}",
            hint="联系管理员为你分配 dept_admin 角色。",
        )
        raise SystemExit(2)
    results = []
    for fp in files:
        try:
            resp = client.upload_files(kb, [fp], source_group=source_group)
            results.append({"file": fp, "ok": True, "response": resp})
            if not skin.json_mode:
                skin.success(f"Uploaded [bold]{os.path.basename(fp)}[/bold] to {kb}")
        except HardwareDatabaseAPIError as e:
            results.append({"file": fp, "ok": False, "error": e.message})
            if not skin.json_mode:
                skin.api_error(f"Upload {os.path.basename(fp)}", e)
    if skin.json_mode:
        skin.json_out(results)
    failed = [r for r in results if not r["ok"]]
    if failed:
        raise SystemExit(1)


@file_group.command("delete", help="Delete a file from a KB.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--name", required=True, help="File name to delete")
@click.option("-y", "--yes", is_flag=True, default=False, help="Skip confirmation.")
@click.pass_context
def file_delete(ctx, kb, name, yes):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    session = ctx.obj.get("session")
    if session and session.role != "system_admin":
        skin.error(
            f"权限不足: 需要 system_admin, 当前身份 {session.role or '未登录'}",
            hint="联系 system_admin 用户执行此操作。",
        )
        raise SystemExit(2)
    if not yes and not click.confirm(f"Delete file '{name}' from {kb}?"):
        skin.info("Cancelled.")
        return
    try:
        client.delete_file(kb, name)
        skin.success(f"File [bold]{name}[/bold] deleted from {kb}.")
    except HardwareDatabaseAPIError as e:
        skin.api_error("Delete file", e)
        raise SystemExit(1)


@file_group.command("chunks", help="Show the parsed chunks of a file.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--file-id", required=True, help="File ID")
@click.pass_context
def file_chunks(ctx, kb, file_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.get_file_chunks(kb, file_id)
        skin.display(data)
    except HardwareDatabaseAPIError as e:
        skin.api_error("Fetch chunks", e)
        raise SystemExit(1)