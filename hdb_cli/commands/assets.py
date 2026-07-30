"""Hardware asset commands — list, view, and manage AI-extracted candidates."""

import click
from ..client import HardwareDatabaseAPIError


@click.group("asset", help="Manage hardware assets.")
def asset_group():
    pass


@asset_group.command("list", help="List assets in a KB.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--query", default="", help="Search query")
@click.pass_context
def asset_list(ctx, kb, query):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_assets(kb, query=query)
        rows = data if isinstance(data, list) else data.get("assets", data.get("data", []))
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No assets found.")
                return
            skin.table(f"Assets in {kb}", ["ID", "Type", "Name", "Model", "Manufacturer", "Status"], [
                (
                    str(r.get("id", "")),
                    r.get("asset_type", ""),
                    r.get("name", ""),
                    r.get("model", ""),
                    r.get("manufacturer", ""),
                    r.get("status", ""),
                )
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.api_error("List assets", e)
        raise SystemExit(1)


@asset_group.command("get", help="Show asset details with evidence.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--asset-id", type=int, required=True, help="Asset ID")
@click.pass_context
def asset_get(ctx, kb, asset_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.get_asset(kb, asset_id)
        if skin.json_mode:
            skin.json_out(data)
        else:
            skin.key_value(f"Asset #{asset_id}", {
                "Type": data.get("asset_type", ""),
                "Name": data.get("name", ""),
                "Model": data.get("model", ""),
                "Manufacturer": data.get("manufacturer", ""),
                "Serial": data.get("serial_number", ""),
                "Version": data.get("version", ""),
                "Status": data.get("status", ""),
                "Evidence": str(len(data.get("evidence", []))),
            })
    except HardwareDatabaseAPIError as e:
        skin.api_error("Get asset", e)
        raise SystemExit(1)


@asset_group.group("candidates", help="Manage AI-extracted asset candidates.")
def candidates_group():
    pass


@candidates_group.command("list", help="List asset candidates.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--status", default="pending", help="Filter: pending/accepted/rejected")
@click.pass_context
def candidates_list(ctx, kb, status):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_asset_candidates(kb, status=status)
        rows = data if isinstance(data, list) else data.get("candidates", data.get("data", []))
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info(f"No {status} candidates.")
                return
            skin.table(f"Asset Candidates ({status})", ["ID", "Type", "Name", "Confidence", "Status"], [
                (str(r.get("id", "")), r.get("asset_type", ""), r.get("name", ""),
                 f"{r.get('confidence', 0):.2f}", r.get("status", ""))
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.api_error("List candidates", e)
        raise SystemExit(1)


@candidates_group.command("generate", help="Trigger AI extraction for a file.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--file-id", required=True, help="File ID to extract from")
@click.pass_context
def candidates_generate(ctx, kb, file_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.generate_asset_candidate(kb, file_id)
        if skin.json_mode:
            skin.json_out(data)
        else:
            skin.success(f"Candidate generated (id={data.get('id', '?')}).")
    except HardwareDatabaseAPIError as e:
        skin.api_error("Generate candidate", e)
        raise SystemExit(1)


@candidates_group.command("accept", help="Accept and confirm an asset candidate.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--candidate-id", type=int, required=True, help="Candidate ID")
@click.option("--asset-type", type=click.Choice(["device", "board", "component", "firmware", "other"]), help="Override asset type")
@click.option("--name", help="Override asset name")
@click.option("--model", help="Override model")
@click.option("--manufacturer", help="Override manufacturer")
@click.option("--serial-number", help="Override serial number")
@click.option("--version", help="Override version")
@click.option("--status", help="Override status")
@click.pass_context
def candidates_accept(ctx, kb, candidate_id, **overrides):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    filtered = {k: v for k, v in overrides.items() if v is not None}
    try:
        data = client.accept_asset_candidate(kb, candidate_id, **filtered)
        if skin.json_mode:
            skin.json_out(data)
        else:
            skin.success(f"Candidate {candidate_id} accepted (asset id={data.get('id', '?')}).")
    except HardwareDatabaseAPIError as e:
        skin.api_error("Accept candidate", e)
        raise SystemExit(1)


@candidates_group.command("reject", help="Reject/ignore an asset candidate.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--candidate-id", type=int, required=True, help="Candidate ID")
@click.pass_context
def candidates_reject(ctx, kb, candidate_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.reject_asset_candidate(kb, candidate_id)
        if skin.json_mode:
            skin.json_out(data)
        else:
            skin.success(f"Candidate {candidate_id} rejected.")
    except HardwareDatabaseAPIError as e:
        skin.api_error("Reject candidate", e)
        raise SystemExit(1)


@asset_group.command("sources", help="List file-to-asset linkage status.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.pass_context
def asset_sources(ctx, kb):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_asset_sources(kb)
        rows = data if isinstance(data, list) else data.get("sources", data.get("data", []))
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No asset sources.")
                return
            skin.table(f"Asset Sources in {kb}", ["File", "Status", "Link Status", "Eligible"], [
                (r.get("file_name", ""), r.get("file_status", ""), r.get("link_status", ""),
                 "✓" if r.get("asset_eligible") else "✗")
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.api_error("List asset sources", e)
        raise SystemExit(1)


# Register sub-group
asset_group.add_command(candidates_group)