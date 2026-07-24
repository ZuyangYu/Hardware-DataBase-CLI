"""Basic structural tests — command registration and argument validation."""

from click.testing import CliRunner
from hdb_cli.main import cli


EXPECTED_GROUPS = {
    "server", "auth", "kb", "file", "query",
    "user", "dept", "perm", "task", "conv",
    "gov", "config", "log",
}


def test_all_groups_registered():
    """Every expected top-level group should be registered on `cli`."""
    registered = set(cli.commands.keys())
    missing = EXPECTED_GROUPS - registered
    assert not missing, f"Missing groups: {missing}"


def test_help_works(runner):
    r = runner.invoke(cli, ["--help"])
    assert r.exit_code == 0
    for grp in EXPECTED_GROUPS:
        assert grp in r.output, f"Group '{grp}' missing from --help"


def test_each_group_help_works(runner):
    """Each group --help should work. Pass a fake token to skip auth prompts."""
    env = {"HDB_TOKEN": "fake"}
    for grp in EXPECTED_GROUPS:
        r = runner.invoke(cli, [grp, "--help"], env=env)
        assert r.exit_code == 0, f"'{grp} --help' failed:\n{r.output}"


def test_missing_required_options(runner):
    """Commands with required options should exit non-zero without them."""
    checks = [
        (["kb", "delete"], "KB_NAME"),  # positional
        (["file", "list"], "--kb"),
        (["file", "delete"], "--kb"),
        (["query", "ask"], "--kb"),
        (["dept", "delete"], "DEPARTMENT_ID"),
        (["perm", "grant"], "--kb"),
        (["task", "list"], "--kb"),
    ]
    for args, expected_hint in checks:
        # Provide a fake token so auth doesn't kick in
        r = runner.invoke(cli, args, env={"HDB_TOKEN": "fake"})
        assert r.exit_code != 0, f"{args} should fail without required args: {r.output}"


def test_auth_status_offline(runner, isolated_config):
    """auth status should work without a network call and no session."""
    r = runner.invoke(cli, ["auth", "status"])
    assert r.exit_code == 0
    assert "logged in" in r.output.lower() or "not logged" in r.output.lower()


def test_auth_status_json(runner, isolated_config):
    r = runner.invoke(cli, ["auth", "status", "--json"])
    assert r.exit_code == 0
    assert "logged_in" in r.output
