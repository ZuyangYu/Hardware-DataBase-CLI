"""Conversation commands."""

import click
from ..client import HardwareDatabaseAPIError


@click.group("conv", help="Manage query conversation sessions.")
def conv_group():
    pass


@conv_group.command("list", help="List conversations.")
@click.option("--kb", default=None, help="Filter by KB name")
@click.pass_context
def conv_list(ctx, kb):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_conversations(kb)
        rows = data if isinstance(data, list) else data.get("conversations", data.get("data", []))
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No conversations.")
                return
            skin.table("Conversations", ["Session ID", "KB", "Title", "Created"], [
                (
                    r.get("session_id", r.get("id", "")),
                    r.get("kb_name", ""),
                    r.get("title", ""),
                    r.get("created_at", ""),
                )
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@conv_group.command("create", help="Create a new conversation.")
@click.option("--kb", required=True)
@click.option("--title", "-t", default=None)
@click.pass_context
def conv_create(ctx, kb, title):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        resp = client.create_conversation(kb, title)
        sid = resp.get("session_id", resp.get("id", "?"))
        skin.success(f"Conversation created: [bold]{sid}[/bold]")
        if skin.json_mode:
            skin.json_out(resp)
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@conv_group.command("delete", help="Delete a conversation.")
@click.argument("session_id")
@click.pass_context
def conv_delete(ctx, session_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        client.delete_conversation(session_id)
        skin.success(f"Conversation {session_id} deleted.")
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@conv_group.command("clear", help="Clear messages in a conversation.")
@click.argument("session_id")
@click.pass_context
def conv_clear(ctx, session_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        client.clear_conversation(session_id)
        skin.success(f"Conversation {session_id} cleared.")
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@conv_group.command("messages", help="Show messages of a conversation.")
@click.argument("session_id")
@click.pass_context
def conv_messages(ctx, session_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.get_conversation_messages(session_id)
        rows = data if isinstance(data, list) else data.get("messages", data.get("data", []))
        if skin.json_mode:
            skin.json_out(rows)
        else:
            for m in rows:
                role = m.get("role", "?")
                content = m.get("content", m.get("text", ""))
                skin.section(f"[{role}]")
                skin.console.print(content)
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@conv_group.command("send", help="Send a message to an existing conversation.")
@click.argument("session_id")
@click.argument("message")
@click.pass_context
def conv_send(ctx, session_id, message):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        resp = client.send_conversation_message(session_id, message)
        if skin.json_mode:
            skin.json_out(resp)
        else:
            skin.display(resp)
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)