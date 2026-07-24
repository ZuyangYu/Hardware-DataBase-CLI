"""Config commands — server config + RAGFlow health."""

import json as _json

import click
from ..client import HardwareDatabaseAPIError


@click.group("config", help="Server-side config (system_admin).")
def config_group():
    pass


@config_group.command("get", help="Show current server config.")
@click.pass_context
def config_get(ctx):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.get_config()
        skin.display(data)
    except HardwareDatabaseAPIError as e:
        skin.api_error("Failed", e)
        raise SystemExit(1)


@config_group.command("set", help="Update server config from a JSON string or @file.")
@click.argument("payload")
@click.pass_context
def config_set(ctx, payload):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    if payload.startswith("@"):
        with open(payload[1:]) as f:
            body = _json.load(f)
    else:
        try:
            body = _json.loads(payload)
        except _json.JSONDecodeError as e:
            skin.error(f"Invalid JSON: {e}")
            raise SystemExit(2)
    try:
        resp = client.update_config(body)
        skin.success("Config updated.")
        if skin.json_mode:
            skin.json_out(resp)
    except HardwareDatabaseAPIError as e:
        skin.api_error("Failed", e)
        raise SystemExit(1)


@config_group.command("ragflow-health", help="Check upstream RAGFlow health.")
@click.pass_context
def config_ragflow_health(ctx):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.ragflow_health()
        skin.display(data)
    except HardwareDatabaseAPIError as e:
        skin.api_error("Failed", e)
        raise SystemExit(1)