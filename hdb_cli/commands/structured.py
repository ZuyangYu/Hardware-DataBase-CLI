"""Structured KB data commands — spreadsheets, circuit designs, schematics, test data."""

import click
from ..client import HardwareDatabaseAPIError


@click.group("structured", help="Browse structured KB data.")
def structured_group():
    pass


# ---- Spreadsheets ---------------------------------------------------------

@structured_group.command("spreadsheets", help="List spreadsheet ledger for a KB.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.pass_context
def structured_spreadsheets(ctx, kb):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_spreadsheets(kb)
        if skin.json_mode:
            skin.json_out(data)
        else:
            totals = data.get("totals", {})
            rows = data.get("rows", [])
            if totals:
                skin.key_value("Spreadsheet Totals", {
                    "Files": str(totals.get("file_count", 0)),
                    "Sheets": str(totals.get("sheet_count", 0)),
                    "Semantic Rows": str(totals.get("semantic_row_count", 0)),
                })
            if rows:
                skin.table("Spreadsheets", ["File", "Sheets", "Rows", "Cells", "Status"], [
                    (r.get("file_name", ""), str(r.get("sheet_count", "")),
                     str(r.get("row_count", "")), str(r.get("cell_count", "")),
                     r.get("status_label", ""))
                    for r in rows
                ])
            elif not totals:
                skin.info("No spreadsheets found.")
    except HardwareDatabaseAPIError as e:
        skin.api_error("List spreadsheets", e)
        raise SystemExit(1)


# ---- Circuit Designs ------------------------------------------------------

@structured_group.group("circuit", help="Browse circuit designs.")
def circuit_group():
    pass


@circuit_group.command("list", help="List circuit designs in a KB.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.pass_context
def circuit_list(ctx, kb):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_circuit_designs(kb)
        if skin.json_mode:
            skin.json_out(data)
        else:
            designs = data.get("designs", [])
            failed = data.get("failed_logs", [])
            if designs:
                skin.table("Circuit Designs", ["Design ID", "Status"], [
                    (d.get("design_id", d.get("id", "")), d.get("status", ""))
                    for d in designs
                ])
            if failed:
                skin.warning(f"{len(failed)} failed design(s)")
            if not designs and not failed:
                skin.info("No circuit designs.")
    except HardwareDatabaseAPIError as e:
        skin.api_error("List circuit designs", e)
        raise SystemExit(1)


@circuit_group.command("get", help="Show circuit design details.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--design-id", required=True, help="Design ID")
@click.option("--net-query", default="", help="Filter nets")
@click.option("--instance-query", default="", help="Filter instances")
@click.pass_context
def circuit_get(ctx, kb, design_id, net_query, instance_query):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.get_circuit_design(kb, design_id, net_query=net_query, instance_query=instance_query)
        if skin.json_mode:
            skin.json_out(data)
        else:
            summary = data.get("summary", {})
            modules = data.get("modules", [])
            nets = data.get("nets", [])
            instances = data.get("instances", [])
            if summary:
                skin.key_value(f"Circuit {design_id}", summary)
            if modules:
                skin.table("Modules", ["Name", "Type"], [(m.get("name", ""), m.get("type", "")) for m in modules])
            if nets:
                skin.table(f"Nets ({len(nets)})", ["Name", "From", "To"], [
                    (n.get("name", ""), n.get("from", ""), n.get("to", "")) for n in nets
                ])
            if instances:
                skin.table(f"Instances ({len(instances)})", ["Ref", "Type", "Value"], [
                    (i.get("refdes", i.get("name", "")), i.get("type", ""), i.get("value", ""))
                    for i in instances
                ])
    except HardwareDatabaseAPIError as e:
        skin.api_error("Get circuit design", e)
        raise SystemExit(1)


@circuit_group.command("delete", help="Delete a circuit design.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--design-id", required=True, help="Design ID")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def circuit_delete(ctx, kb, design_id, yes):
    skin = ctx.obj["skin"]
    if not yes:
        click.confirm(f"Delete circuit design {design_id} from {kb}?", abort=True)
    client = ctx.obj["client"]
    try:
        data = client.delete_circuit_design(kb, design_id)
        if skin.json_mode:
            skin.json_out(data)
        else:
            skin.success(data.get("message", f"Deleted {design_id}."))
    except HardwareDatabaseAPIError as e:
        skin.api_error("Delete circuit design", e)
        raise SystemExit(1)


@circuit_group.command("parse-log", help="Show circuit design parse log.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--design-id", required=True, help="Design ID")
@click.pass_context
def circuit_parse_log(ctx, kb, design_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.get_circuit_parse_log(kb, design_id)
        if skin.json_mode:
            skin.json_out(data)
        else:
            if data.get("exists"):
                content = data.get("content", "")
                if data.get("truncated"):
                    skin.warning("Log truncated (max 64KB shown)")
                print(content)
            else:
                skin.info("No parse log available.")
    except HardwareDatabaseAPIError as e:
        skin.api_error("Get parse log", e)
        raise SystemExit(1)


# ---- Modules --------------------------------------------------------------

@structured_group.command("modules", help="List modules in a KB (optionally filter by design).")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--design-id", default="", help="Design ID (empty = all designs)")
@click.pass_context
def structured_modules(ctx, kb, design_id):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_modules(kb, design_id=design_id)
        rows = data if isinstance(data, list) else data.get("rows", [])
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No modules found.")
                return
            skin.table("Modules", list(rows[0].keys()) if rows else [], [
                tuple(str(r.get(k, "")) for k in (list(rows[0].keys()) if rows else []))
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.api_error("List modules", e)
        raise SystemExit(1)


# ---- Test Reports ---------------------------------------------------------

@structured_group.command("test-reports", help="List test reports in a KB.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.pass_context
def structured_test_reports(ctx, kb):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_test_reports(kb)
        rows = data if isinstance(data, list) else data.get("rows", [])
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No test reports.")
                return
            skin.table("Test Reports", list(rows[0].keys()) if rows else [], [
                tuple(str(r.get(k, "")) for k in (list(rows[0].keys()) if rows else []))
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.api_error("List test reports", e)
        raise SystemExit(1)


# ---- Test Measurements ----------------------------------------------------

@structured_group.command("test-measurements", help="Search test measurements.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--query", default="", help="Search query")
@click.option("--limit", type=int, default=100, help="Max results (1-500)")
@click.pass_context
def structured_test_measurements(ctx, kb, query, limit):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_test_measurements(kb, query=query, limit=limit)
        rows = data if isinstance(data, list) else data.get("rows", [])
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No measurements found.")
                return
            skin.table("Test Measurements", list(rows[0].keys()) if rows else [], [
                tuple(str(r.get(k, "")) for k in (list(rows[0].keys()) if rows else []))
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.api_error("List test measurements", e)
        raise SystemExit(1)


# ---- Schematics -----------------------------------------------------------

@structured_group.group("schematic", help="Browse schematic pages.")
def schematic_group():
    pass


@schematic_group.command("list", help="List schematic designs in a KB.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.pass_context
def schematic_list(ctx, kb):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_schematics(kb)
        if skin.json_mode:
            skin.json_out(data)
        else:
            designs = data.get("designs", [])
            if not designs:
                skin.info("No schematics.")
                return
            skin.table("Schematic Designs", ["Design ID", "Pages", "Labels", "Regions"], [
                (d.get("design_id", ""), str(d.get("page_count", "")),
                 str(d.get("label_count", "")), str(d.get("module_region_count", "")))
                for d in designs
            ])
    except HardwareDatabaseAPIError as e:
        skin.api_error("List schematics", e)
        raise SystemExit(1)


@schematic_group.command("get-page", help="Get a specific schematic page.")
@click.option("--kb", required=True, help="Knowledge base name")
@click.option("--design-id", required=True, help="Design ID")
@click.option("--page-number", type=int, required=True, help="Page number")
@click.pass_context
def schematic_get_page(ctx, kb, design_id, page_number):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.get_schematic_page(kb, design_id, page_number)
        if skin.json_mode:
            skin.json_out(data)
        else:
            skin.key_value(f"Schematic {design_id} page {page_number}", {
                "Width": str(data.get("width", "")),
                "Height": str(data.get("height", "")),
                "Text length": str(len(data.get("text", ""))),
                "Labels": str(len(data.get("labels", []))),
                "Module Regions": str(len(data.get("module_regions", []))),
                "Screenshots": str(len(data.get("screenshots", []))),
            })
            text = data.get("text", "")
            if text:
                skin.section("Text")
                print(text[:2000] + ("..." if len(text) > 2000 else ""))
    except HardwareDatabaseAPIError as e:
        skin.api_error("Get schematic page", e)
        raise SystemExit(1)


# Register sub-groups
structured_group.add_command(circuit_group)
structured_group.add_command(schematic_group)