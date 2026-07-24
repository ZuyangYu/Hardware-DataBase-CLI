"""Server commands — health check."""

import click
from ..client import HardwareDatabaseAPIError


@click.group("server", help="Server health & status.")
def server_group():
    pass


@server_group.command("health", help="Ping the API server and show status.")
@click.pass_context
def server_health(ctx):
    client = ctx.obj["client"]
    skin = ctx.obj["skin"]
    try:
        data = client.health()
        if skin.json_mode:
            skin.json_out(data)
        else:
            healthy = data.get("status", "ok")
            version = data.get("version", "?")
            skin.success(f"Healthy — [bold]hw-db v{version}[/bold]")
            skin.table("Server Info", ["Key", "Value"], list(data.items()))
    except HardwareDatabaseAPIError as e:
        skin.error(f"Server unreachable: {e.message}")
        raise SystemExit(1)