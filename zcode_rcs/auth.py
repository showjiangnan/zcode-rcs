import asyncio
import hmac
import secrets
import sqlite3
import time
from collections import OrderedDict
from dataclasses import dataclass

from .config import Config, key_digest, load_keys


@dataclass(frozen=True)
class Session:
    id: str
    identity: str
    version: int
    role: str
    name: str
    expires: float
    created: float


class AuthStore:
    def __init__(self, config: Config):
        self.config = config
        self.keys = {}
        self.lock = asyncio.Lock()
        self.rates: OrderedDict[str, tuple[float, int]] = OrderedDict()
        self.path = config.data_dir / "control.sqlite3"
        self.instance_id = ""

    async def initialize(self):
        await asyncio.to_thread(self.config.data_dir.mkdir, parents=True, exist_ok=True, mode=0o700)
        await self.reload_keys()
        def initialize():
            with sqlite3.connect(self.path) as db:
                db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, digest TEXT UNIQUE, identity TEXT, version INTEGER, role TEXT, name TEXT, expires REAL, created REAL)")
                db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
                db.execute("INSERT OR IGNORE INTO meta VALUES ('instance', ?)", (secrets.token_hex(16),))
                return db.execute("SELECT value FROM meta WHERE key='instance'").fetchone()[0]
        self.instance_id = await asyncio.to_thread(initialize)
        await asyncio.to_thread(self.path.chmod, 0o600)

    async def reload_keys(self):
        self.keys = await asyncio.to_thread(load_keys, self.config.keys_file)

    def rate_limit(self, address: str):
        now = time.monotonic()
        start, count = self.rates.pop(address, (now, 0))
        if now - start > 60:
            start, count = now, 0
        self.rates[address] = (start, count + 1)
        while len(self.rates) > 4096:
            self.rates.popitem(last=False)
        if count >= 12:
            raise PermissionError("RATE_LIMITED")

    async def login(self, key: str, role: str, name: str):
        digest = key_digest(key)
        identity = next((k for k in self.keys.values() if hmac.compare_digest(k.digest, digest)), None)
        if not identity:
            raise PermissionError("AUTH_FAILED")
        token = secrets.token_urlsafe(48)
        now = time.time()
        session = Session(secrets.token_hex(16), identity.id, identity.version, role, name, now + self.config.session_seconds, now)
        async with self.lock:
            def insert():
                with sqlite3.connect(self.path) as db:
                    db.execute("DELETE FROM sessions WHERE expires < ?", (now,))
                    if db.execute("SELECT count(*) FROM sessions").fetchone()[0] >= self.config.max_sessions:
                        raise PermissionError("SESSION_LIMIT")
                    db.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?)", (session.id, key_digest(token), session.identity, session.version, role, name, session.expires, now))
            await asyncio.to_thread(insert)
        return session, token

    async def resolve(self, token: str = "", session_id: str = "") -> Session:
        def query():
            with sqlite3.connect(self.path) as db:
                clause, value = ("id", session_id) if session_id else ("digest", key_digest(token))
                return db.execute(f"SELECT id,identity,version,role,name,expires,created FROM sessions WHERE {clause}=?", (value,)).fetchone()
        row = await asyncio.to_thread(query)
        if not row or row[6] + 30 * 86400 < time.time() or row[5] < time.time():
            raise PermissionError("SESSION_EXPIRED")
        session = Session(*row)
        key = self.keys.get(session.identity)
        if not key or key.version != session.version:
            raise PermissionError("KEY_REVOKED")
        return session

    async def refresh(self, session: Session):
        await self.resolve(session_id=session.id)
        expires = min(time.time() + self.config.session_seconds, session.created + 30 * 86400)
        def update():
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE sessions SET expires=? WHERE id=?", (expires, session.id))
        await asyncio.to_thread(update)
        return expires

    async def revoke(self, session_id: str):
        def delete():
            with sqlite3.connect(self.path) as db:
                db.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        await asyncio.to_thread(delete)

    async def clients(self, identity: str):
        def list_clients():
            with sqlite3.connect(self.path) as db:
                return [{"id": row[0], "name": row[1], "expiresAt": row[2], "createdAt": row[3]} for row in db.execute("SELECT id,name,expires,created FROM sessions WHERE identity=? AND role='client' AND expires>?", (identity, time.time()))]
        return await asyncio.to_thread(list_clients)
