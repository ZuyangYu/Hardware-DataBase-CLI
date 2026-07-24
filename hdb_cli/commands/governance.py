"""Governance commands — stats & KB summaries."""

import click
from ..client import HardwareDatabaseAPIError


@click.group("gov", help="Governance stats & KB summaries.")
def gov_group():
    pass


@gov_group.command("stats", help="Show global governance stats.")
@click.pass_context
def gov_stats(ctx):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.governance_stats()
        skin.display(data)
    except HardwareDatabaseAPIError as e:
        skin.api_error("Failed", e)
        raise SystemExit(1)


@gov_group.command("kb-summaries", help="Show per-KB governance summaries.")
@click.pass_context
def gov_kb_summaries(ctx):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.governance_kb_summaries()
        rows = data if isinstance(data, list) else data.get("summaries", data.get("data", []))
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No KB summaries.")
                return
            skin.table("KB Summaries", ["KB", "Files", "Chunks", "Size"], [
                (
                    r.get("kb_name", r.get("name", "")),
                    str(r.get("file_count", "")),
                    str(r.get("chunk_count", "")),
                    str(r.get("total_size", "")),
                )
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.api_error("Failed", e)
        raise SystemExit(1)