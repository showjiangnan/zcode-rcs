import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class KeyIdentity:
    id: str
    digest: str
    version: int = 1


@dataclass(frozen=True)
class Config:
    origin: str
    data_dir: Path
    web_dir: Path
    keys_file: Path
    session_seconds: int = 3600
    max_sessions: int = 128
    max_devices: int = 16
    max_attachments: int = 64
    max_frame_bytes: int = 16 * 1024 * 1024
    max_queue_bytes: int = 32 * 1024 * 1024
    allow_loopback_http: bool = False

    def validate(self):
        parsed = urlsplit(self.origin)
        loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not (
            self.allow_loopback_http and loopback and parsed.scheme == "http"
        ):
            raise ValueError("RCS_PUBLIC_ORIGIN must use HTTPS (HTTP is loopback-development only)")
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ValueError("RCS_PUBLIC_ORIGIN must be a credential-free origin")
        if not parsed.hostname or not 60 <= self.session_seconds <= 86400:
            raise ValueError("Invalid origin or session expiry")
        return self


def load_keys(path: Path) -> dict[str, KeyIdentity]:
    values = json.loads(path.read_text())
    result = {}
    for value in values:
        if set(value) - {"id", "sha256", "version"}:
            raise ValueError("Unknown key configuration field")
        key = KeyIdentity(value["id"], value["sha256"], value.get("version", 1))
        if not isinstance(key.id, str) or not key.id or len(key.id) > 64:
            raise ValueError("Invalid key identity")
        if not isinstance(key.digest, str) or len(key.digest) != 64 or any(c not in "0123456789abcdef" for c in key.digest):
            raise ValueError("Keys must be SHA-256 digests of generated high-entropy secrets")
        if type(key.version) is not int or key.version < 1 or key.id in result:
            raise ValueError("Duplicate identity or invalid version")
        result[key.id] = key
    if not result:
        raise ValueError("At least one key is required; anonymous control is disabled")
    return result


def key_digest(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def from_env() -> Config:
    return Config(
        origin=os.environ["RCS_PUBLIC_ORIGIN"].rstrip("/"),
        data_dir=Path(os.environ.get("RCS_DATA_DIR", "data")),
        web_dir=Path(os.environ.get("RCS_WEB_DIR", "web")),
        keys_file=Path(os.environ.get("RCS_KEYS_FILE", "data/keys.json")),
        session_seconds=int(os.environ.get("RCS_SESSION_SECONDS", "3600")),
        allow_loopback_http=os.environ.get("RCS_ALLOW_LOOPBACK_HTTP") == "1",
    ).validate()
