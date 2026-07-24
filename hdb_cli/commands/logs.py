"""Log commands — audit logs, query traces."""

import click
from ..client import HardwareDatabaseAPIError


@click.group("log", help="Audit & query logs (admin).")
def log_group():
    pass


@log_group.command("audit", help="List audit-log entries.")
@click.option("--user-id", type=int, default=None)
@click.option("--action", default=None)
@click.option("--limit", type=int, default=None)
@click.pass_context
def log_audit(ctx, user_id, action, limit):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.audit_logs(user_id=user_id, action=action, limit=limit)
        rows = data if isinstance(data, list) else data.get("logs", data.get("data", []))
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No audit logs.")
                return
            skin.table("Audit Logs", ["Time", "User", "Action", "Target"], [
                (
                    r.get("timestamp", r.get("created_at", "")),
                    r.get("username", str(r.get("user_id", ""))),
                    r.get("action", ""),
                    r.get("target", ""),
                )
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@log_group.command("audit-stats", help="Audit-log aggregate stats.")
@click.pass_context
def log_audit_stats(ctx):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        skin.display(client.audit_stats())
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@log_group.command("audit-actions", help="Known audit-log action types.")
@click.pass_context
def log_audit_actions(ctx):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        skin.display(client.audit_actions())
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@log_group.command("query-traces", help="Recent query traces.")
@click.option("--user-id", type=int, default=None)
@click.option("--kb", default=None)
@click.option("--limit", type=int, default=None)
@click.pass_context
def log_query_traces(ctx, user_id, kb, limit):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.query_logs(user_id=user_id, kb_name=kb, limit=limit)
        rows = data if isinstance(data, list) else data.get("traces", data.get("data", []))
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No traces.")
                return
            skin.table("Query Traces", ["Time", "Trace ID", "User", "KB", "Query"], [
                (
                    r.get("timestamp", ""),
                    r.get("trace_id", ""),
                    r.get("username", str(r.get("user_id", ""))),
                    r.get("kb_name", ""),
                    (r.get("query", "") or "")[:60],
                )
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@log_group.command("query-stats", help="Query-log aggregate stats.")
@click.pass_context
def log_query_stats(ctx):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        skin.display(client.query_stats())
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)


@log_group.command("trace-evidence", help="Show retrieval evidence for a query trace.")
@click.argument("trace_id")
@click.pass_context
def log_trace_evidence(ctx, trace_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        skin.display(client.trace_evidence(trace_id))
    except HardwareDatabaseAPIError as e:
        skin.error(f"Failed: {e.message}")
        raise SystemExit(1)