"""Shell completion helper — hdb completion bash/zsh/fish."""

import click


@click.command("completion", help="Print shell completion script.")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion_cmd(shell):
    """Print instructions for enabling shell tab completion.

    Example:
      eval "$(_HDB_COMPLETE=bash_source hdb)"       # bash
      eval "$(_HDB_COMPLETE=zsh_source hdb)"        # zsh
      _HDB_COMPLETE=fish_source hdb | source        # fish
    """
    if shell == "bash":
        click.echo('eval "$(_HDB_COMPLETE=bash_source hdb)"')
        click.echo("# Add the line above to ~/.bashrc for persistent completion.")
    elif shell == "zsh":
        click.echo('eval "$(_HDB_COMPLETE=zsh_source hdb)"')
        click.echo("# Add the line above to ~/.zshrc for persistent completion.")
    elif shell == "fish":
        click.echo("_HDB_COMPLETE=fish_source hdb | source")
        click.echo("# Add the line above to ~/.config/fish/config.fish for persistent completion.")


@click.command("version", help="Show CLI version.")
def version_cmd():
    """Show CLI version (bare 'version' subcommand)."""
    try:
        from importlib.metadata import version as _v
        v = _v("hardware-database-cli")
    except Exception:
        v = "0.1.0"
    click.echo(f"hdb {v}")