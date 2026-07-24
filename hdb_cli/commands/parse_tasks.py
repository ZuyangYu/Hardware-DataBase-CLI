"""Parse-task commands."""

import click
from ..client import HardwareDatabaseAPIError


@click.group("task", help="KB parse-task management.")
def task_group():
    pass


@task_group.command("list", help="List parse tasks for a KB.")
@click.option("--kb", required=True)
@click.pass_context
def task_list(ctx, kb):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_parse_tasks(kb)
        rows = data if isinstance(data, list) else data.get("tasks", data.get("data", []))
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No parse tasks.")
                return
            skin.table(f"Parse tasks in {kb}", ["Task ID", "File", "Status", "Progress"], [
                (
                    r.get("task_id", r.get("id", "")),
                    r.get("file_name", r.get("filename", "")),
                    r.get("status", ""),
                    str(r.get("progress", "")),
                )
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@task_group.command("clear-finished", help="Delete all finished parse tasks in a KB.")
@click.option("--kb", required=True)
@click.pass_context
def task_clear(ctx, kb):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        resp = client.clear_finished_parse_tasks(kb)
        skin.success("Finished tasks cleared.")
        if skin.json_mode:
            skin.json_out(resp)
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@task_group.command("delete", help="Delete a specific parse task.")
@click.option("--kb", required=True)
@click.argument("task_id")
@click.pass_context
def task_delete(ctx, kb, task_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        client.delete_parse_task(kb, task_id)
        skin.success(f"Task {task_id} deleted.")
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@task_group.command("pause", help="Pause a parse task (RAGFlow may not support).")
@click.option("--kb", required=True)
@click.argument("task_id")
@click.pass_context
def task_pause(ctx, kb, task_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        resp = client.pause_parse_task(kb, task_id)
        skin.success(f"Pause requested for task {task_id}.")
        if skin.json_mode:
            skin.json_out(resp)
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@task_group.command("resume", help="Resume a parse task (RAGFlow may not support).")
@click.option("--kb", required=True)
@click.argument("task_id")
@click.pass_context
def task_resume(ctx, kb, task_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        resp = client.resume_parse_task(kb, task_id)
        skin.success(f"Resume requested for task {task_id}.")
        if skin.json_mode:
            skin.json_out(resp)
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)