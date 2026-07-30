"""Evaluation commands — RAGAS evaluation runs, dataset upload, compare."""

import click
from ..client import HardwareDatabaseAPIError


@click.group("eval", help="RAGAS evaluation management (system_admin).")
def eval_group():
    pass


@eval_group.group("run", help="Manage evaluation runs.")
def run_group():
    pass


@run_group.command("list", help="List evaluation runs.")
@click.option("--output-root", help="Override output root path")
@click.pass_context
def run_list(ctx, output_root):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.list_evaluation_runs(output_root=output_root)
        rows = data if isinstance(data, list) else data.get("runs", [])
        if skin.json_mode:
            skin.json_out(rows)
        else:
            if not rows:
                skin.info("No evaluation runs.")
                return
            skin.table("Evaluation Runs", ["Run ID", "Status", "Has Summary"], [
                (r.get("run_id", ""), r.get("status", ""), "✓" if r.get("has_summary") else "✗")
                for r in rows
            ])
    except HardwareDatabaseAPIError as e:
        skin.api_error("List runs", e)
        raise SystemExit(1)


@run_group.command("create", help="Create a new evaluation run.")
@click.option("--dataset-path", required=True, help="Path to dataset file")
@click.option("--mode", type=click.Choice(["online", "offline"]), default="online")
@click.option("--score-enabled/--no-score", default=True, help="Enable scoring")
@click.option("--sample-id", multiple=True, help="Sample IDs to include (repeatable)")
@click.option("--tag", multiple=True, help="Tags to filter by (repeatable)")
@click.option("--snapshot-path", help="Snapshot path (required for offline mode)")
@click.option("--output-root", help="Override output root path")
@click.pass_context
def run_create(ctx, dataset_path, mode, score_enabled, sample_id, tag, snapshot_path, output_root):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    sample_ids = list(sample_id) if sample_id else None
    tags = list(tag) if tag else None
    try:
        data = client.create_evaluation_run(
            dataset_path, mode=mode, score_enabled=score_enabled,
            sample_ids=sample_ids, tags=tags,
            snapshot_path=snapshot_path, output_root=output_root,
        )
        if skin.json_mode:
            skin.json_out(data)
        else:
            skin.success(f"Run created (id={data.get('run_id', '?')}).")
            skin.display(data)
    except HardwareDatabaseAPIError as e:
        skin.api_error("Create run", e)
        raise SystemExit(1)


@run_group.command("start", help="Start an evaluation run.")
@click.option("--run-id", required=True, help="Run ID")
@click.option("--output-root", help="Override output root path")
@click.pass_context
def run_start(ctx, run_id, output_root):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.start_evaluation_run(run_id, output_root=output_root)
        if skin.json_mode:
            skin.json_out(data)
        else:
            skin.success(f"Run {run_id} started.")
    except HardwareDatabaseAPIError as e:
        skin.api_error("Start run", e)
        raise SystemExit(1)


@run_group.command("pause", help="Pause a running evaluation.")
@click.option("--run-id", required=True, help="Run ID")
@click.option("--output-root", help="Override output root path")
@click.pass_context
def run_pause(ctx, run_id, output_root):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.pause_evaluation_run(run_id, output_root=output_root)
        if skin.json_mode:
            skin.json_out(data)
        else:
            skin.success(f"Run {run_id} paused.")
    except HardwareDatabaseAPIError as e:
        skin.api_error("Pause run", e)
        raise SystemExit(1)


@run_group.command("resume", help="Resume a paused evaluation.")
@click.option("--run-id", required=True, help="Run ID")
@click.option("--output-root", help="Override output root path")
@click.pass_context
def run_resume(ctx, run_id, output_root):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.resume_evaluation_run(run_id, output_root=output_root)
        if skin.json_mode:
            skin.json_out(data)
        else:
            skin.success(f"Run {run_id} resumed.")
    except HardwareDatabaseAPIError as e:
        skin.api_error("Resume run", e)
        raise SystemExit(1)


@run_group.command("cancel", help="Cancel an evaluation run.")
@click.option("--run-id", required=True, help="Run ID")
@click.option("--output-root", help="Override output root path")
@click.pass_context
def run_cancel(ctx, run_id, output_root):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.cancel_evaluation_run(run_id, output_root=output_root)
        if skin.json_mode:
            skin.json_out(data)
        else:
            skin.success(f"Run {run_id} cancelled.")
    except HardwareDatabaseAPIError as e:
        skin.api_error("Cancel run", e)
        raise SystemExit(1)


@run_group.command("get", help="Get evaluation run details.")
@click.option("--run-id", required=True, help="Run ID")
@click.option("--output-root", help="Override output root path")
@click.pass_context
def run_get(ctx, run_id, output_root):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.get_evaluation_run(run_id, output_root=output_root)
        if skin.json_mode:
            skin.json_out(data)
        else:
            summary = data.get("summary")
            if summary:
                skin.key_value(f"Run {run_id}", {k: str(v) for k, v in summary.items()})
            skin.display(data)
    except HardwareDatabaseAPIError as e:
        skin.api_error("Get run", e)
        raise SystemExit(1)


@run_group.command("compare", help="Compare two evaluation runs.")
@click.option("--run-id", required=True, help="Current run ID")
@click.option("--baseline", required=True, help="Baseline run ID to compare against")
@click.option("--output-root", help="Override output root path")
@click.pass_context
def run_compare(ctx, run_id, baseline, output_root):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.compare_evaluation_run(run_id, baseline, output_root=output_root)
        if skin.json_mode:
            skin.json_out(data)
        else:
            current = data.get("current", {})
            baseline_data = data.get("baseline", {})
            if current:
                skin.key_value(f"Current ({run_id})", {k: str(v) for k, v in current.items()})
            if baseline_data:
                skin.key_value(f"Baseline ({baseline})", {k: str(v) for k, v in baseline_data.items()})
    except HardwareDatabaseAPIError as e:
        skin.api_error("Compare runs", e)
        raise SystemExit(1)


# ---- Dataset Upload -------------------------------------------------------

@eval_group.command("upload-dataset", help="Upload a .jsonl evaluation dataset.")
@click.option("--file", "file_path", required=True, type=click.Path(exists=True), help="Path to .jsonl file")
@click.option("--output-root", help="Override output root path")
@click.pass_context
def eval_upload_dataset(ctx, file_path, output_root):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.upload_evaluation_dataset(file_path, output_root=output_root)
        if skin.json_mode:
            skin.json_out(data)
        else:
            skin.success(f"Dataset uploaded: {data.get('file_name', '')} ({data.get('sample_count', '?')} samples)")
    except HardwareDatabaseAPIError as e:
        skin.api_error("Upload dataset", e)
        raise SystemExit(1)


# Register sub-groups
eval_group.add_command(run_group)