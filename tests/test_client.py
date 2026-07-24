"""Client tests using respx to mock httpx transports."""

import httpx
import respx
import pytest

from hdb_cli.client import HardwareDatabaseClient, HardwareDatabaseAPIError


BASE = "http://test-server:8000"


def _client():
    return HardwareDatabaseClient(base_url=BASE, token="test-token")


@respx.mock
def test_health_ok():
    respx.get(f"{BASE}/health").mock(
        return_value=httpx.Response(200, json={"ok": True, "version": "1.0"})
    )
    with _client() as c:
        assert c.health() == {"ok": True, "version": "1.0"}


@respx.mock
def test_bearer_header_present():
    route = respx.get(f"{BASE}/whoami").mock(
        return_value=httpx.Response(200, json={"username": "alice", "role": "user"})
    )
    with _client() as c:
        c.whoami()
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer test-token"


@respx.mock
def test_login_sets_token():
    respx.post(f"{BASE}/login").mock(
        return_value=httpx.Response(200, json={"token": "new-tok", "user": {"username": "alice", "role": "user"}})
    )
    with HardwareDatabaseClient(base_url=BASE) as c:
        c.login("alice", "pw")
        assert c.token == "new-tok"


@respx.mock
def test_error_raises_api_error():
    respx.get(f"{BASE}/kbs").mock(
        return_value=httpx.Response(403, json={"detail": "Permission denied"})
    )
    with _client() as c:
        with pytest.raises(HardwareDatabaseAPIError) as ei:
            c.list_kbs()
        assert ei.value.status_code == 403
        assert "Permission denied" in ei.value.message


@respx.mock
def test_upload_multipart():
    route = respx.post(f"{BASE}/kbs/my-kb/files").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    tmp.write(b"hello world")
    tmp.close()
    try:
        with _client() as c:
            c.upload_files("my-kb", [tmp.name], source_group="test")
        assert route.called
    finally:
        os.unlink(tmp.name)


@respx.mock
def test_query_sse_stream():
    sse_body = (
        "event: delta\ndata: {\"text\": \"Hello \"}\n\n"
        "event: delta\ndata: {\"text\": \"world\"}\n\n"
        "event: done\ndata: {\"total_tokens\": 5}\n\n"
    )
    respx.post(f"{BASE}/query").mock(
        return_value=httpx.Response(
            200,
            content=sse_body,
            headers={"content-type": "text/event-stream"},
        )
    )
    with _client() as c:
        events = list(c.query("my-kb", "hi?"))
    kinds = [e[0] for e in events]
    assert "delta" in kinds
    assert "done" in kinds
    text = "".join(e[1].get("text", "") for e in events if e[0] == "delta")
    assert "Hello world" in text


def test_connection_error_wrapped():
    # unreachable host
    with HardwareDatabaseClient(base_url="http://127.0.0.1:1", token="x", timeout=1.0) as c:
        with pytest.raises(HardwareDatabaseAPIError):
            c.health()
