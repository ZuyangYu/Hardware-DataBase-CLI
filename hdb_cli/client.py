"""HTTP client for the Hardware DataBase API.

Wraps httpx.Client with bearer-token auth, unified error handling, and
SSE streaming support for the /query endpoint. One method per REST endpoint.
"""

from __future__ import annotations

import json
from typing import Any, Iterator

import httpx


API_PREFIX = "/api/v1"


class HardwareDatabaseAPIError(Exception):
    """API-level error from the Hardware DataBase server."""

    def __init__(self, message: str, status_code: int = 0, hint: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.hint = hint

    def __str__(self) -> str:
        parts = [f"HTTP {self.status_code}" if self.status_code else "Connection"]
        parts.append(self.message)
        if self.hint:
            parts.append(f"→ {self.hint}")
        return " | ".join(parts)


def _connection_error(base_url: str) -> HardwareDatabaseAPIError:
    return HardwareDatabaseAPIError(
        f"无法连接到 API 服务器 ({base_url})。",
        hint="检查后端是否启动 (hardware-database-server) 或用 --api-url 指定其他地址。",
    )


def _prefixed(path: str) -> str:
    """Prepend API_PREFIX to path unless it's the bare health probe."""
    if path == "/health":
        return path
    return API_PREFIX + path


# Static hints for common HTTP status codes. Command-specific hints are
# added on top of these in the command layer via `hint=` on APIError.
_STATUS_HINTS = {
    401: "会话已过期或 token 无效 — 运行 `hdb auth login` 重新登录。",
    403: "权限不足 — 运行 `hdb auth whoami` 查看当前角色，或联系管理员授权。",
    404: "资源不存在 — 检查名称/ID 是否拼写正确。",
    422: "请求参数校验失败 — 检查必填字段和字段类型。",
    500: "服务端内部错误 — 非客户端凭据问题，请联系管理员或稍后重试。",
    502: "上游服务不可达 — 后端到 RAGFlow/LLM 的连接失败。",
    503: "服务不可用 — 后端正在启动或过载，请稍后重试。",
    504: "上游服务超时 — RAGFlow/LLM 响应过慢。",
}


class HardwareDatabaseClient:
    """Thin, dependency-light HTTP client for the Hardware DataBase API.

    - Default base URL: ``http://127.0.0.1:8001`` (matches the server).
    - All routes are prefixed with ``/api/v1`` automatically (except ``/health``).
    - Auth: ``Authorization: Bearer <token>`` header when token is set.
    - Errors: any HTTP >=400 raises :class:`HardwareDatabaseAPIError`.
    - Streaming: ``query()`` yields ``(event, payload)`` tuples parsed
      from the ``text/event-stream`` response of ``POST /query``.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8001",
        token: str | None = None,
        timeout: float = 30.0,
        verbose_logger=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._timeout = timeout
        self._verbose = verbose_logger  # callable(str) -> None, or None
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

    def set_verbose_logger(self, fn) -> None:
        """Install a callback for verbose HTTP tracing. Pass None to disable."""
        self._verbose = fn

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
        path = _prefixed(path)
        try:
            if self._verbose:
                self._verbose(
                    f"[b]Request:[/b] {method} {self.base_url}{path}"
                    + (f"\n[b]Body:[/b] {json.dumps(json_body, ensure_ascii=False, default=str)}" if json_body else "")
                )
            resp = self._client.request(
                method,
                path,
                json=json_body,
                params=params,
                files=files,
                data=data,
                timeout=timeout or self._timeout,
            )
            if self._verbose:
                ctype = resp.headers.get("content-type", "")
                body_preview = resp.text[:300] if "text" in ctype else "…"
                self._verbose(
                    f"[b]Response:[/b] {resp.status_code} {path}"
                    + (f"\n[b]Body:[/b] {body_preview}" if body_preview else "")
                )
        except httpx.ConnectError:
            raise _connection_error(self.base_url)
        except httpx.TimeoutException:
            raise HardwareDatabaseAPIError(
                f"请求超时 ({method} {path})",
                status_code=0,
                hint="后端或上游服务响应过慢，可稍后重试或联系管理员。",
            )
        return self._handle(resp)

    def _get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(
        self, path: str, json_body: Any = None, *,
        params: dict | None = None, files: Any = None, timeout: float | None = None,
    ) -> Any:
        return self._request("POST", path, json_body=json_body, params=params, files=files, timeout=timeout or 60.0)

    def _put(self, path: str, json_body: Any = None) -> Any:
        return self._request("PUT", path, json_body=json_body, timeout=60.0)

    def _delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def _stream(self, path: str, json_body: Any) -> Iterator[tuple[str, Any]]:
        """POST + SSE stream. Yields (event, payload) tuples."""
        path = _prefixed(path)
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
                    if line.startswith("event:"):
                        current_event = line[6:].strip()
                    elif line.startswith("data:"):
                        payload = line[5:].lstrip()
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
        # Attach a generic hint for this status code. Command handlers
        # that know the context can override hint via the exception.
        hint = _STATUS_HINTS.get(resp.status_code)
        return HardwareDatabaseAPIError(str(detail), resp.status_code, hint=hint)

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

    def resolve_user_id(self, user: str | int) -> int:
        """Accept either a numeric id or a username; return the id.

        Raises HardwareDatabaseAPIError if the username is unknown.
        """
        if isinstance(user, int) or (isinstance(user, str) and user.isdigit()):
            return int(user)
        users = self.list_users()
        rows = users if isinstance(users, list) else users.get("users", users.get("data", []))
        for u in rows:
            if u.get("username") == user:
                return int(u.get("id"))
        raise HardwareDatabaseAPIError(
            f"未找到用户名 '{user}'",
            status_code=404,
            hint="运行 `hdb user list` 查看现有用户，或改用数字 ID。",
        )

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
        return self._put(f"/users/{user_id}/active", {"is_active": active})

    def reset_user_password(self, user_id: int, new_password: str) -> Any:
        return self._put(f"/users/{user_id}/password", {"new_password": new_password})

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
            f"/conversations/{session_id}/messages", {"role": "user", "content": message}
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

    # ---- KB permissions: revoke (DELETE) --------------------------------
    def revoke_kb_permission(self, kb_name: str, user_id: int) -> Any:
        return self._delete(f"/kbs/{kb_name}/permissions/{user_id}")

    # ---- Hardware Assets ------------------------------------------------
    def list_assets(self, kb_name: str, query: str = "") -> Any:
        params = {"query": query} if query else None
        return self._get(f"/kbs/{kb_name}/assets", params=params)

    def get_asset(self, kb_name: str, asset_id: int) -> Any:
        return self._get(f"/kbs/{kb_name}/assets/{asset_id}")

    def list_asset_candidates(self, kb_name: str, status: str = "pending") -> Any:
        return self._get(f"/kbs/{kb_name}/asset-candidates", params={"status": status})

    def list_asset_sources(self, kb_name: str) -> Any:
        return self._get(f"/kbs/{kb_name}/asset-sources")

    def generate_asset_candidate(self, kb_name: str, file_id: str) -> Any:
        return self._post(f"/kbs/{kb_name}/asset-candidates/generate", {"file_id": file_id})

    def accept_asset_candidate(
        self, kb_name: str, candidate_id: int,
        asset_type: str | None = None, name: str | None = None,
        model: str | None = None, manufacturer: str | None = None,
        serial_number: str | None = None, version: str | None = None,
        status: str | None = None, owner_user_id: int | None = None,
        attributes: dict | None = None,
    ) -> Any:
        body: dict[str, Any] = {}
        if asset_type is not None: body["asset_type"] = asset_type
        if name is not None: body["name"] = name
        if model is not None: body["model"] = model
        if manufacturer is not None: body["manufacturer"] = manufacturer
        if serial_number is not None: body["serial_number"] = serial_number
        if version is not None: body["version"] = version
        if status is not None: body["status"] = status
        if owner_user_id is not None: body["owner_user_id"] = owner_user_id
        if attributes is not None: body["attributes"] = attributes
        return self._post(f"/kbs/{kb_name}/asset-candidates/{candidate_id}/accept", body)

    def reject_asset_candidate(self, kb_name: str, candidate_id: int) -> Any:
        return self._post(f"/kbs/{kb_name}/asset-candidates/{candidate_id}/reject")

    # ---- Structured KB data ---------------------------------------------
    def list_spreadsheets(self, kb_name: str) -> Any:
        return self._get(f"/kbs/{kb_name}/structured/spreadsheets")

    def list_circuit_designs(self, kb_name: str) -> Any:
        return self._get(f"/kbs/{kb_name}/structured/circuit-designs")

    def get_circuit_design(
        self, kb_name: str, design_id: str,
        net_query: str = "", instance_query: str = "",
    ) -> Any:
        params = {}
        if net_query: params["net_query"] = net_query
        if instance_query: params["instance_query"] = instance_query
        return self._get(f"/kbs/{kb_name}/structured/circuit-designs/{design_id}", params=params or None)

    def delete_circuit_design(self, kb_name: str, design_id: str) -> Any:
        return self._delete(f"/kbs/{kb_name}/structured/circuit-designs/{design_id}")

    def get_circuit_parse_log(self, kb_name: str, design_id: str) -> Any:
        return self._get(f"/kbs/{kb_name}/structured/circuit-designs/{design_id}/parse-log")

    def list_modules(self, kb_name: str, design_id: str = "") -> Any:
        return self._get(f"/kbs/{kb_name}/structured/modules", params={"design_id": design_id})

    def list_test_reports(self, kb_name: str) -> Any:
        return self._get(f"/kbs/{kb_name}/structured/test-reports")

    def list_test_measurements(self, kb_name: str, query: str = "", limit: int = 100) -> Any:
        return self._get(
            f"/kbs/{kb_name}/structured/test-measurements",
            params={"query": query, "limit": limit},
        )

    def list_schematics(self, kb_name: str) -> Any:
        return self._get(f"/kbs/{kb_name}/structured/schematics")

    def get_schematic_page(self, kb_name: str, design_id: str, page_number: int) -> Any:
        return self._get(f"/kbs/{kb_name}/structured/schematics/{design_id}/pages/{page_number}")

    # ---- Evaluation ----------------------------------------------------
    def list_evaluation_runs(self, output_root: str | None = None) -> Any:
        params = {"output_root": output_root} if output_root else None
        return self._get("/evaluation/runs", params=params)

    def create_evaluation_run(
        self, dataset_path: str, mode: str = "online",
        score_enabled: bool = True, sample_ids: list[str] | None = None,
        tags: list[str] | None = None, snapshot_path: str | None = None,
        output_root: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {"dataset_path": dataset_path, "mode": mode, "score_enabled": score_enabled}
        if sample_ids: body["sample_ids"] = sample_ids
        if tags: body["tags"] = tags
        if snapshot_path: body["snapshot_path"] = snapshot_path
        params = {"output_root": output_root} if output_root else None
        return self._post("/evaluation/runs", body, params=params)

    def upload_evaluation_dataset(self, file_path: str, output_root: str | None = None) -> Any:
        """Upload a .jsonl dataset file for evaluation (multipart)."""
        params = {"output_root": output_root} if output_root else None
        with open(file_path, "rb") as f:
            name = file_path.rsplit("/", 1)[-1]
            return self._request("POST", "/evaluation/datasets", files={"file": (name, f)}, params=params)

    def start_evaluation_run(self, run_id: str, output_root: str | None = None) -> Any:
        params = {"output_root": output_root} if output_root else None
        return self._post(f"/evaluation/runs/{run_id}/start", params=params)

    def pause_evaluation_run(self, run_id: str, output_root: str | None = None) -> Any:
        params = {"output_root": output_root} if output_root else None
        return self._post(f"/evaluation/runs/{run_id}/pause", params=params)

    def resume_evaluation_run(self, run_id: str, output_root: str | None = None) -> Any:
        params = {"output_root": output_root} if output_root else None
        return self._post(f"/evaluation/runs/{run_id}/resume", params=params)

    def cancel_evaluation_run(self, run_id: str, output_root: str | None = None) -> Any:
        params = {"output_root": output_root} if output_root else None
        return self._post(f"/evaluation/runs/{run_id}/cancel", params=params)

    def get_evaluation_run(self, run_id: str, output_root: str | None = None) -> Any:
        params = {"output_root": output_root} if output_root else None
        return self._get(f"/evaluation/runs/{run_id}", params=params)

    def compare_evaluation_run(self, run_id: str, baseline: str, output_root: str | None = None) -> Any:
        params: dict[str, Any] = {"baseline": baseline}
        if output_root: params["output_root"] = output_root
        return self._get(f"/evaluation/runs/{run_id}/compare", params=params)

    # ---- Metrics -------------------------------------------------------
    def task_metrics(self, hours: int = 24) -> Any:
        return self._get("/task-metrics", params={"hours": hours})

    # ---- LLM Health ----------------------------------------------------
    def llm_health(self) -> Any:
        return self._get("/health/llm")
