"""Basic structural tests — command registration and argument validation."""

from click.testing import CliRunner
from hdb_cli.main import cli


EXPECTED_GROUPS = {
    "server", "auth", "kb", "file", "query",
    "user", "dept", "perm", "task", "conv",
    "gov", "config", "log", "doctor",
}

EXPECTED_LEAF_COMMANDS = {"completion", "version"}


def test_all_groups_registered():
    """Every expected top-level group should be registered on `cli`."""
    registered = set(cli.commands.keys())
    missing = EXPECTED_GROUPS - registered
    assert not missing, f"Missing groups: {missing}"
    missing_leaves = EXPECTED_LEAF_COMMANDS - registered
    assert not missing_leaves, f"Missing leaf commands: {missing_leaves}"


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


def test_version_command(runner):
    """The `version` subcommand should print something version-like."""
    r = runner.invoke(cli, ["version"])
    assert r.exit_code == 0
    assert "hdb" in r.output.lower()


def test_completion_bash(runner):
    """`completion bash` should print an eval-able snippet."""
    r = runner.invoke(cli, ["completion", "bash"])
    assert r.exit_code == 0
    assert "_HDB_COMPLETE" in r.output


def test_doctor_config_json(runner, isolated_config):
    """`doctor config --json` should emit a JSON config summary."""
    r = runner.invoke(cli, ["--json", "doctor", "config"], env={"HDB_TOKEN": "fake"})
    assert r.exit_code == 0
    assert "api_url" in r.output


def test_kb_delete_yes_flag(runner):
    """`kb delete --yes` should skip the confirmation prompt (no stdin needed)."""
    r = runner.invoke(cli, ["kb", "delete", "some-kb", "--yes"], env={"HDB_TOKEN": "fake"})
    # We expect exit code != 0 because the API isn't reachable, but there must
    # be NO 'Aborted!' or interactive-prompt line.
    assert "Aborted" not in r.output
    assert "Delete knowledge base 'some-kb'" not in r.output


def test_perm_grant_accepts_user_flag(runner):
    """`perm grant --user` should be accepted (not just --user-id)."""
    r = runner.invoke(
        cli,
        ["perm", "grant", "--kb", "x", "--user", "alice", "--permission", "read"],
        env={"HDB_TOKEN": "fake"},
    )
    # We don't have a live server; but the error must NOT be about a bad option.
    assert "No such option" not in r.output


def test_query_ask_json_flag(runner):
    """`query ask --json` should be accepted as a local option."""
    r = runner.invoke(
        cli,
        ["query", "ask", "--kb", "x", "--json", "test question"],
        env={"HDB_TOKEN": "fake"},
    )
    assert "No such option" not in r.output


def test_verbose_flag(runner):
    """`-v` should be accepted as a global option (parsing check only)."""
    r = runner.invoke(cli, ["-v", "auth", "status"], env={"HDB_TOKEN": "fake"})
    assert r.exit_code == 0
    # Being accepted means no 'No such option' error.
    assert "No such option" not in r.output


def test_auth_status_json_local(runner, isolated_config):
    """`auth status --json` should work as a local option, not just global."""
    r = runner.invoke(cli, ["auth", "status", "--json"])
    assert r.exit_code == 0
    assert "logged_in" in r.output
