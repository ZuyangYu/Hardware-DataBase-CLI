"""Query command — SSE streaming ask against a KB."""

import json as _json

import click
from ..client import HardwareDatabaseAPIError


@click.group("query", help="Ask questions against a knowledge base.")
def query_group():
    pass


@query_group.command("ask", help="Ask a question (streaming answer).")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--thread-id", default=None, help="Optional conversation thread ID")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output as JSON.")
@click.argument("question")
@click.pass_context
def query_ask(ctx, kb, thread_id, json_mode, question):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    if json_mode:
        skin.json_mode = True
    try:
        if skin.json_mode:
            answer_parts: list[str] = []
            summary: dict | None = None
            for event, data in client.query(kb, question, thread_id=thread_id):
                if event == "delta":
                    if isinstance(data, dict):
                        answer_parts.append(data.get("text", ""))
                elif event in ("done", "data"):
                    if isinstance(data, dict):
                        summary = data
                elif event == "error":
                    skin.json_out({"error": data})
                    raise SystemExit(1)
            summary = summary or {}
            summary["answer"] = "".join(answer_parts)
            skin.json_out(summary)
        else:
            skin.section(f"[{kb}] {question}")
            print()
            for event, data in client.query(kb, question, thread_id=thread_id):
                if event == "delta" and isinstance(data, dict):
                    print(data.get("text", ""), end="", flush=True)
                elif event == "error":
                    msg = data.get("message", str(data)) if isinstance(data, dict) else str(data)
                    skin.error(f"\nQuery error: {msg}")
                    raise SystemExit(1)
            print()
    except HardwareDatabaseAPIError as e:
        skin.api_error("Query", e)
        if e.status_code == 403:
            skin.next_step(
                f"perm list --kb {kb}                     检查该 KB 的权限",
                f"perm grant --kb {kb} --user <你> --permission read  为自己授权",
            )
        raise SystemExit(1)