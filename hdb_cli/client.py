"""HTTP client for the Hardware DataBase API.

Wraps httpx.Client with bearer-token auth, unified error handling, and
SSE streaming support for the /query endpoint. One method per REST endpoint.
"""

from __future__ import annotations

import json
from typing import Any, Iterator

import httpx


class HardwareDatabaseAPIError(Exception):
    """API-level error from the Hardware DataBase server."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _connection_error(base_url: str) -> HardwareDatabaseAPIError:
    return HardwareDatabaseAPIError(
        f"无法连接到 API 服务器 ({base_url})。请先运行 hardware-database-server。"
    )


class HardwareDatabaseClient:
    """Thin, dependency-light HTTP client for the Hardware DataBase API.

    - Default base URL: ``http://127.0.0.1:8000`` (matches the server).
    - Auth: ``Authorization: Bearer <token>`` header when token is set.
    - Errors: any HTTP >=400 raises :class:`HardwareDatabaseAPIError`.
    - Streaming: ``query()`` yields ``(event, payload)`` tuples parsed
      from the ``text/event-stream`` response of ``POST /query``.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        token: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._timeout = timeout
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )

    # ── lifecycle ────────────────────────────────────────────────────────

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HardwareDatabaseClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def set_token(self, token: str) -> None:
        self.token = token
        self._client.headers["Authorization"] = f"Bearer {token}"

    # ── low-level helpers ────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: dict | None = None,
        files: Any = None,
        data: Any = None,
        timeout: float | None = None,
    ) -> Any:
        try:
            resp = self._client.request(
                method,
                path,
                json=json_body,
                params=params,
                files=files,
                data=data,
                timeout=timeout or self._timeout,
            )
        except httpx.ConnectError:
            raise _connection_error(self.base_url)
        except httpx.TimeoutException:
            raise HardwareDatabaseAPIError(
                f"请求超时 ({method} {path})。",
                status_code=0,
            )
        return self._handle(resp)

    def _get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(self, path: str, json_body: Any = None, timeout: float | None = None) -> Any:
        return self._request("POST", path, json_body=json_body, timeout=timeout or 60.0)

    def _put(self, path: str, json_body: Any = None) -> Any:
        return self._request("PUT", path, json_body=json_body, timeout=60.0)

    def _delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def _stream(self, path: str, json_body: Any) -> Iterator[tuple[str, Any]]:
        """POST + SSE stream. Yields (event, payload) tuples."""
        try:
            with self._client.stream(
                "POST", path, json=json_body, timeout=120.0
            ) as resp:
                if resp.status_code >= 400:
                    resp.read()
                    raise self._error_from_response(resp)
                current_event = "delta"
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if line.startswith("event: "):
                        current_event = line[7:].strip()
                    elif line.startswith("data: "):
                        payload = line[6:]
                        try:
                            yield (current_event, json.loads(payload))
                        except json.JSONDecodeError:
                            yield (current_event, {"text": payload})
                        current_event = "delta"
                    elif line.startswith(":"):
                        continue
                    else:
                        try:
                            yield ("delta", json.loads(line))
                        except json.JSONDecodeError:
                            yield ("delta", {"text": line})
        except httpx.ConnectError:
            raise _connection_error(self.base_url)

    @staticmethod
    def _handle(resp: httpx.Response) -> Any:
        if resp.status_code >= 400:
            raise HardwareDatabaseClient._error_from_response(resp)
        if not resp.content:
            return {}
        ctype = resp.headers.get("content-type", "")
        if "application/json" in ctype:
            return resp.json()
        return resp.text

    @staticmethod
    def _error_from_response(resp: httpx.Response) -> HardwareDatabaseAPIError:
        try:
            body = resp.json()
            detail = body.get("detail", body) if isinstance(body, dict) else body
        except Exception:
            detail = resp.text or f"HTTP {resp.status_code}"
        return HardwareDatabaseAPIError(str(detail), resp.status_code)

    # ────────────────────────────────────────────────────────────────────
    # API methods — one per backend endpoint, grouped by area
    # ────────────────────────────────────────────────────────────────────

    # ---- Health ------------------------------------------------------
    def health(self) -> Any:
        """GET /health"""
        return self._get("/health")

    # ---- Auth --------------------------------------------------------
    def login(self, username: str, password: str) -> Any:
        """POST /login → {token, user}. Auto-sets bearer token on success."""
        resp = self._post("/login", {"username": username, "password": password})
        if isinstance(resp, dict) and resp.get("token"):
            self.set_token(resp["token"])
        return resp

    def whoami(self) -> Any:
        """GET /whoami"""
        return self._get("/whoami")

    def logout(self) -> Any:
        """POST /logout — server-side session revoke."""
        return self._post("/logout")

    # ---- Users -------------------------------------------------------
    def list_users(self) -> Any:
        return self._get("/users")

    def create_user(
        self,
        username: str,
        password: str,
        role: str,
        department_id: int | None = None,
    ) -> Any:
        body = {"username": username, "password": password, "role": role}
        if department_id is not None:
            body["department_id"] = department_id
        return self._post("/users", body)

    def set_user_active(self, user_id: int, active: bool) -> Any:
        return self._put(f"/users/{user_id}/active", {"active": active})

    def reset_user_password(self, user_id: int, new_password: str) -> Any:
        return self._put(f"/users/{user_id}/password", {"password": new_password})

    # ---- Departments -------------------------------------------------
    def list_departments(self) -> Any:
        return self._get("/departments")

    def create_department(self, name: str, description: str | None = None) -> Any:
        body = {"name": name}
        if description:
            body["description"] = description
        return self._post("/departments", body)

    def delete_department(self, department_id: int) -> Any:
        return self._delete(f"/departments/{department_id}")

    # ---- Knowledge bases --------------------------------------------
    def list_kbs(self) -> Any:
        return self._get("/kbs")

    def create_kb(self, name: str, description: str | None = None) -> Any:
        body = {"name": name}
        if description:
            body["description"] = description
        return self._post("/kbs", body)

    def delete_kb(self, kb_name: str) -> Any:
        return self._delete(f"/kbs/{kb_name}")

    # ---- KB files ----------------------------------------------------
    def list_files(self, kb_name: str) -> Any:
        return self._get(f"/kbs/{kb_name}/files")

    def upload_files(
        self,
        kb_name: str,
        file_paths: list[str],
        source_group: str | None = None,
    ) -> Any:
        """POST /kbs/{kb}/files — multipart upload of one or more files."""
        files = []
        handles = []
        try:
            for fp in file_paths:
                name = fp.rsplit("/", 1)[-1]
                fh = open(fp, "rb")
                handles.append(fh)
                files.append(("files", (name, fh)))
            data = {"source_group": source_group} if source_group else None
            return self._request(
                "POST",
                f"/kbs/{kb_name}/files",
                files=files,
                data=data,
                timeout=120.0,
            )
        finally:
            for fh in handles:
                fh.close()

    def delete_file(self, kb_name: str, file_name: str) -> Any:
        return self._delete(f"/kbs/{kb_name}/files/{file_name}")

    def get_file_chunks(self, kb_name: str, file_id: str) -> Any:
        return self._get(f"/kbs/{kb_name}/files/{file_id}/chunks")

    # ---- KB permissions ---------------------------------------------
    def list_kb_permissions(self, kb_name: str) -> Any:
        return self._get(f"/kbs/{kb_name}/permissions")

    def grant_kb_permission(
        self, kb_name: str, user_id: int, permission: str
    ) -> Any:
        return self._post(
            f"/kbs/{kb_name}/permissions",
            {"user_id": user_id, "permission": permission},
        )

    def assign_kb(self, kb_name: str, department_id: int) -> Any:
        return self._put(f"/kbs/{kb_name}/assign", {"department_id": department_id})

    # ---- Parse tasks -------------------------------------------------
    def list_parse_tasks(self, kb_name: str) -> Any:
        return self._get(f"/kbs/{kb_name}/parse-tasks")

    def clear_finished_parse_tasks(self, kb_name: str) -> Any:
        return self._delete(f"/kbs/{kb_name}/parse-tasks/finished")

    def delete_parse_task(self, kb_name: str, task_id: str) -> Any:
        return self._delete(f"/kbs/{kb_name}/parse-tasks/{task_id}")

    def pause_parse_task(self, kb_name: str, task_id: str) -> Any:
        return self._post(f"/kbs/{kb_name}/parse-tasks/{task_id}/pause")

    def resume_parse_task(self, kb_name: str, task_id: str) -> Any:
        return self._post(f"/kbs/{kb_name}/parse-tasks/{task_id}/resume")

    # ---- Query (SSE) -------------------------------------------------
    def query(
        self,
        kb_name: str,
        question: str,
        history: list | None = None,
        thread_id: str | None = None,
    ) -> Iterator[tuple[str, Any]]:
        body: dict[str, Any] = {
            "kb_name": kb_name,
            "query": question,
            "history": history or [],
        }
        if thread_id:
            body["thread_id"] = thread_id
        yield from self._stream("/query", body)

    # ---- Conversations ----------------------------------------------
    def list_conversations(self, kb_name: str | None = None) -> Any:
        params = {"kb_name": kb_name} if kb_name else None
        return self._get("/conversations", params=params)

    def create_conversation(
        self, kb_name: str, title: str | None = None
    ) -> Any:
        body: dict[str, Any] = {"kb_name": kb_name}
        if title:
            body["title"] = title
        return self._post("/conversations", body)

    def get_conversation(self, session_id: str) -> Any:
        return self._get(f"/conversations/{session_id}")

    def delete_conversation(self, session_id: str) -> Any:
        return self._delete(f"/conversations/{session_id}")

    def clear_conversation(self, session_id: str) -> Any:
        return self._post(f"/conversations/{session_id}/clear")

    def get_conversation_messages(self, session_id: str) -> Any:
        return self._get(f"/conversations/{session_id}/messages")

    def send_conversation_message(self, session_id: str, message: str) -> Any:
        return self._post(
            f"/conversations/{session_id}/messages", {"message": message}
        )

    # ---- Governance -------------------------------------------------
    def governance_stats(self) -> Any:
        return self._get("/governance/stats")

    def governance_kb_summaries(self) -> Any:
        return self._get("/governance/kb-summaries")

    # ---- Config -----------------------------------------------------
    def get_config(self) -> Any:
        return self._get("/config")

    def update_config(self, config: dict) -> Any:
        return self._put("/config", config)

    def ragflow_health(self) -> Any:
        return self._get("/health/ragflow")

    # ---- Logs -------------------------------------------------------
    def audit_logs(self, **filters) -> Any:
        return self._get("/logs/audit", params={k: v for k, v in filters.items() if v is not None})

    def audit_stats(self) -> Any:
        return self._get("/logs/audit/stats")

    def audit_actions(self) -> Any:
        return self._get("/logs/audit/actions")

    def query_logs(self, **filters) -> Any:
        return self._get("/logs/query", params={k: v for k, v in filters.items() if v is not None})

    def query_stats(self) -> Any:
        return self._get("/logs/query/stats")

    def trace_evidence(self, trace_id: str) -> Any:
        return self._get(f"/logs/query/{trace_id}/evidence")
