"""Bearer-token config loading + saving.

Precedence (highest first):
  1. --token CLI option
  2. HDB_TOKEN env var
  3. ~/.config/hdb-cli/session.json (written by `hdb auth login`)

API base URL:
  1. --api-url CLI option
  2. HDB_API_URL env var
  3. Saved session file
  4. http://127.0.0.1:8001
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict


CONFIG_DIR = Path(os.environ.get("HDB_CONFIG_DIR", os.path.expanduser("~/.config/hdb-cli")))
TOKEN_FILE = CONFIG_DIR / "session.json"
DEFAULT_URL = "http://127.0.0.1:8001"


@dataclass
class Session:
    api_url: str
    token: str | None = None
    username: str | None = None
    role: str | None = None
    department_id: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


def load_session(cli_url: str | None = None, cli_token: str | None = None) -> Session:
    """Resolve api_url + token with the documented precedence."""
    api_url = cli_url or os.environ.get("HDB_API_URL") or DEFAULT_URL
    token = cli_token or os.environ.get("HDB_TOKEN")
    username = role = department_id = None
    if not token and TOKEN_FILE.exists():
        try:
            data = json.loads(TOKEN_FILE.read_text())
            token = data.get("token")
            username = data.get("username")
            role = data.get("role")
            department_id = data.get("department_id")
            # If session file also stored api_url and user didn't override, use it
            if not cli_url and not os.environ.get("HDB_API_URL"):
                api_url = data.get("api_url", api_url)
        except Exception:
            pass
    return Session(
        api_url=api_url.rstrip("/"),
        token=token,
        username=username,
        role=role,
        department_id=department_id,
    )


def save_session(api_url: str, token: str, username: str, role: str,
                 department_id: str | None = None) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "api_url": api_url,
        "token": token,
        "username": username,
        "role": role,
    }
    if department_id is not None:
        payload["department_id"] = department_id
    TOKEN_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass


def save(session: Session) -> None:
    """Convenience: save a Session dataclass."""
    save_session(
        api_url=session.api_url,
        token=session.token or "",
        username=session.username or "",
        role=session.role or "",
        department_id=session.department_id,
    )


def clear_session() -> bool:
    """Remove the on-disk session. Returns True if a file was actually removed."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        return True
    return False


# Alias for symmetry with save()
clear = clear_session
