import argparse
import json
import os
import secrets
from pathlib import Path

import uvicorn

from .config import key_digest, from_env


def main():
    parser = argparse.ArgumentParser(description="ZCode user-owned RCS")
    sub = parser.add_subparsers(dest="command", required=True)
    key = sub.add_parser("keygen", help="Generate a secret and a server hash configuration")
    key.add_argument("--id", default="owner")
    key.add_argument("--output", type=Path, required=True)
    key.add_argument("--secret-output", type=Path, required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8030)
    args = parser.parse_args()
    if args.command == "keygen":
        secret = secrets.token_urlsafe(48)
        created = []
        try:
            for path, value in [(args.output, json.dumps([{"id": args.id, "sha256": key_digest(secret), "version": 1}], indent=2)), (args.secret_output, secret + "\n")]:
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                # 凭据从首次创建即为 0600；第二个路径冲突时只回收本次创建的文件。
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                created.append(path)
                with os.fdopen(fd, "w") as stream:
                    stream.write(value)
                    stream.flush()
                    os.fsync(stream.fileno())
        except OSError:
            for path in created:
                path.unlink(missing_ok=True)
            raise
        print("Credential files created with mode 0600. Keep the secret on your own devices.")
    else:
        config = from_env()
        index = config.web_dir / "index.html"
        metadata = config.web_dir / "build-info.json"
        if not index.is_file() or not metadata.is_file():
            parser.error("A complete compatible production Web bundle is required")
        compatibility = json.loads(metadata.read_text())
        if any(compatibility.get(name) != expected for name, expected in [("bridgeVersion", 1), ("rpcCodec", 1), ("agentWire", 3)]):
            parser.error("Web bundle is incompatible with this server")
        # 一个 worker 拥有全部在线连接；多 worker 需要先提供跨进程路由。
        uvicorn.run("zcode_rcs.app:create_app", factory=True, host=args.host, port=args.port,
                    workers=1, ws_max_size=16 * 1024 * 1024 + 25, ws_max_queue=8,
                    ws_ping_interval=20, ws_ping_timeout=30, access_log=False)


if __name__ == "__main__":
    main()
