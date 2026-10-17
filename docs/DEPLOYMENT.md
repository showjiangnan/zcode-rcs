# Deployment and operations / 部署运维

Use Python 3.12+, the checked-in `uv.lock`, a dedicated HTTPS origin root and one Uvicorn worker. Included Web/SDK/protocol assets must match bridge 1 / RPC codec 1 / Agent wire 3. Subpath hosting and multi-worker/horizontal routing are not supported.

## Environment

| Variable                | Meaning                                                                           |
| ----------------------- | --------------------------------------------------------------------------------- |
| RCS_PUBLIC_ORIGIN       | Required exact public HTTPS origin; no credentials, query, fragment or extra path |
| RCS_KEYS_FILE           | Server identity digest JSON, default data/keys.json                               |
| RCS_DATA_DIR            | Authentication SQLite directory, default data; retain between restarts            |
| RCS_WEB_DIR             | Matching production Web bundle, default web                                       |
| RCS_SESSION_SECONDS     | Sliding expiry 60–86400 seconds; default 3600; absolute limit 30 days             |
| RCS_ALLOW_LOOPBACK_HTTP | Set 1 only for localhost/127.0.0.1/::1 development                                |

Generate secrets with `uv run zcode-rcs keygen --output data/keys.json --secret-output data/owner.key`. Never commit either file. Provide only `keys.json` to the server process/container; use the plaintext file only on authorized clients. A self-selected key must be high entropy and 32–512 characters. Plain passwords are not supported by the SHA-256 key format.

## Native server

Run `uv sync --frozen`, then a service manager invoking `uv run --no-sync zcode-rcs serve --host 127.0.0.1 --port 8030`, with the environment above and a non-root OS user. Put TLS reverse proxy in front. Nginx must pass HTTP/1.1 WebSocket upgrades and disable proxy buffering. Idle timeouts must exceed heartbeat intervals. Restrict the backend port to loopback/private container networking. Preserve request Origin; do not enable wildcard credential CORS or bypass TLS checks.

## Docker

`deploy/compose.yaml` builds the bundled server and Web. Set `RCS_PUBLIC_ORIGIN` and `RCS_KEYS_FILE` before `docker compose -f deploy/compose.yaml up -d --build`. The server runs as uid 10001; its `/data` volume stores only auth metadata. Ensure the mounted server hash file is readable by that uid while keeping it out of public paths. Plaintext secrets are not placed in the image.

Liveness: `GET /api/rcs/v1/health`. Compatibility: `GET /api/rcs/v1/meta`. A healthy relay does not imply that an execution computer is online. Device/Host discovery is authenticated.

## Updates, backups and rotation

Release 1.1.2 ships SDK 1.1.2 and Web 3.15.2; wire versions remain 1 / 1 / 3. Update all of `zcode_rcs/`, Python package/lock files, `web/`, `sdk/`, and `protocol/` together. Stop the old process first and retain its authentication database and key files. The exporter uses staging, an exclusive lease and rollback; the three directory replacements are not an online filesystem transaction. Do not export into a directory while it is serving requests.

Build from current desktop source with `ZCODE_ENV=production pnpm --filter @zcode/web build`, then run `node scripts/build-rcs-assets.mjs /path/to/zcode-rcs`. `web/rcs-source.json` identifies build inputs; `web/build-info.json` records `rcsVersion`, `sdkVersion`, `sourceFingerprint` and `artifactFingerprint`. The artifact digest is SHA-256 of JSON-encoded sorted `[relativePath, sha256(fileBytes)]` pairs across `sdk/`, `protocol/` and `web/`, excluding `web/build-info.json` itself. Paths use `/` separators.

An interrupted export may leave `.rcs-assets-export.lock` or `.rcs-assets-stage-*`. Confirm that its exporter has exited before removing a stale lease. A rollback failure retains `previous/` under the staging directory for recovery; restore the complete old set before restarting. Do not delete authentication storage during recovery.

Back up the SQLite auth database and keys configuration using a consistent SQLite backup or stop the server briefly. There is no server conversation/PTY/file backup because those facts belong to the execution computer. Restarting the server drops live attachments; clients rediscover and restore from desktop runtime facts. Retaining auth storage preserves existing session identity and revocations.

Update the complete server/Web/SDK/protocol set, keep data volume, then restart one instance. Compatibility mismatch fails explicitly. To rotate, atomically replace the digest configuration, increment the identity version and update desktop/browser keys. The 10-second sweep revokes old sessions and closes their sockets; removal of an identity revokes it. Do not mutate a file partially while the server reads it. Invalid key configuration does not replace the last validated configuration; fix it and observe successful authentication before declaring rotation finished.

Revoke one client from desktop RCS settings or DELETE `/api/rcs/v1/clients/{id}`. Logging out revokes that session and its attachments. Disable RCS on desktop to close the device connection immediately; accepted local work continues.

## Limits and recovery

Default maximums: 128 auth sessions, 16 online devices, 64 attachments, 64 pending requests per device, 20-second device request timeout, 5-second unauthenticated socket timeout, 16 MiB binary payload, 32 MiB/512-frame connection queue and 64 KiB HTTP request body. Large media uses 512 KiB blocks. Slow consumers receive backpressure; sustained overflow disconnects and requires snapshot/resume. A production proxy must also enforce sensible TLS connection limits.

Desktop ZCode must remain open with an existing Host and allowed workspaces. Sleeping/exited/offline execution computers cannot serve tasks. A browser refresh does not start another Agent. A Host crash changes its generation; stale attachments are rejected and clients rediscover the live Host. Local model provider failures remain model failures, not relay authentication failures.
