# ZCode RCS

A user-operated Python bridge with a complete responsive ZCode Web UI. Keep the Feiyu ZCode desktop app open, enter your bridge endpoint and key, and access allowed workspaces from desktop or mobile browsers. Agents, model requests, tools and session state run on your own execution computer. The server authenticates clients and forwards data.

[中文](README.md) · [Desktop source and installation](https://github.com/showjiangnan/zcode-feiyu) · [API and SDK](docs/API.md) · [Deployment](docs/DEPLOYMENT.md) · [Security](docs/SECURITY.md)

Current bundle: **RCS / SDK 1.1.2, Web 3.14.7**. This update adds workflow run settings, progress, logs and save operations with the paired shared Web protocol. Conversation/project navigation, model configuration, orchestration, memory and image displays remain available. Native MCP Apps/Gen UI page sandboxes remain local desktop capabilities with accurate Web fallbacks. Conversation execution and subagents continue to use the connected desktop runtime.

The shared model menu includes reasoning and speed sliders, defaulting to Standard speed. ChatGPT subscriptions offer catalog-available tiers; Teamorouter Responses uses each model's Fast / Ultrafast settings. Single/double lightning icons show the selection, while the actual tier from successful responses is displayed separately. Selecting Fast does not prove acceleration. Other providers retain their existing paths. Teamorouter settings show the balance, currency and recommended top-up link; the recommendation does not imply a partnership. Proactive controls remain hidden when disabled.

ChatGPT subscription models use an existing desktop connection. Remote clients can read safe status and public model capabilities and refresh the catalog; sign-in and account management stay on Desktop. Shared errors retain bounded incomplete reasons without raw responses or credentials. External imports are performed on Desktop; remote clients may read and continue imported sessions within the original granted workspace. The 2026-10-15 update synchronizes source and paired assets without publishing a new Release.

## Validation and platform scope

This update synchronizes production shared Web, SDK and protocol assets and verifies local Python-bridge sign-in, restore and sign-out interactions. CUA preview stacking and closure handling remain local desktop capabilities; remote browsers receive no native preview-frame, OS-permission or private-credential interface. Mac results do not validate the current Windows native build or real devices. The paired desktop release provides macOS arm64 only, with no Windows installer. Public-cloud TLS, physical-phone keyboards and all third-party services still require environment-specific validation.

## Local setup

Python 3.12+ and uv are required. Compatible Web and SDK assets are included; the server does not require Node or Electron.

```bash
uv sync --frozen
uv run zcode-rcs keygen --output data/keys.json --secret-output data/owner.key
export RCS_PUBLIC_ORIGIN=http://127.0.0.1:8030
export RCS_ALLOW_LOOPBACK_HTTP=1
export RCS_KEYS_FILE="$PWD/data/keys.json"
uv run zcode-rcs serve --port 8030
```

Keep `owner.key` on your devices. The server stores SHA-256 digests in `keys.json`; generated credential files use mode 0600. HTTP is permitted only for explicit loopback development.

1. Open **Settings → Remote services → RCS** in a compatible Feiyu desktop app.
2. Enter the endpoint and generated key, name the device, select allowed workspaces, validate and save with RCS enabled. No workspace is exposed by default.
3. Open the bridge origin, enter the same key and select the online device, window and workspace.
4. Keep desktop ZCode open. Offline or sleeping computers show a reconnect state; the bridge does not start cloud agents or accept offline tasks.

## Production

Deploy at a dedicated HTTPS origin root, such as `https://zcode.example.com`:

```bash
export RCS_PUBLIC_ORIGIN=https://zcode.example.com
export RCS_KEYS_FILE="$PWD/data/keys.json"
docker compose -f deploy/compose.yaml up -d --build
```

The container exposes port 8030 on loopback only. Include [the Nginx example](deploy/nginx.conf) inside your TLS server block. Use one worker; horizontal routing is not implemented. See [deployment and operations](docs/DEPLOYMENT.md) for backups, updates and key rotation.

## Capabilities

| Capability                   | Implementation                                                                                                                         |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Responsive conversations     | Shared desktop React Root and components, mobile/desktop layouts, independent bridge authentication                                    |
| Sessions and orchestration   | Same desktop runtime and command admission, standard/coordinator/swarm, history, permissions, stop and recovery                        |
| Memory, workflows and images | Existing Host services and settings; image/model providers remain configured on the execution computer                                 |
| Files and artifacts          | Host path validation, existing transactional attachment uploads, bounded media ranges, content-hash guarded text editing API           |
| Terminal recovery            | Host-owned PTYs, reconnect to the same ID, bounded sequence replay and deduplication; disconnect does not kill the shell               |
| Public integrations          | REST control plane, explicit RPC allowlist and schemas, standalone SDK with injectable fetch/WebSocket transport                       |
| Access control               | OS-protected desktop secret, server key digests, expiring/revocable sessions, workspace grants, Origin checks and bounded flow control |

This is a bridge to your local ZCode. Native OS dialogs and permissions remain desktop capabilities. SSH and existing mobile chat bots are managed through desktop settings. A finished mini-program or mobile app is not included; the same public API is available for custom clients.

## Updating Web and SDK assets

Python source is in `zcode_rcs/`. The authoritative TypeScript UI/SDK source is in the desktop repository. This repository ships standalone deployable `web/`, `sdk/`, and `protocol/` assets without maintaining another conversation UI:

```bash
ZCODE_ENV=production pnpm --filter @zcode/web build
node scripts/build-rcs-assets.mjs /path/to/zcode-rcs
```

Compatibility: bridge **1**, RPC codec **1**, Agent wire **3**. Check `/api/rcs/v1/meta` and `web/build-info.json`; the latter records paired versions, source fingerprint and artifact fingerprint. The exporter rejects missing or stale Web builds, validates staged assets, and restores the previous asset set if replacement fails. Stop the service before installing a complete release, retain `data/` and key configuration, then restart. Internal methods are not automatically exposed. Local specifications and test records are excluded from production publication.

## Data and trust

The bridge stores authentication/revocation metadata in SQLite and keeps bounded routing buffers in memory. It does not persist conversations, prompts, repository files, memories or terminal output. Requested content passes through your server. TLS terminates there; the server operator is trusted and this version does not promise end-to-end encryption. Anyone holding your valid shared key can control its identity group.

Apache-2.0. Preserve [LICENSE](LICENSE) and [third-party notices](web/THIRD-PARTY-NOTICES.md).

The current companion build adds reviewed workflow synchronization and save-from-run APIs. Native MCP Apps/Gen UI page sandboxes remain local desktop capabilities; the responsive Web UI uses platform fallbacks. The bridge still forwards to the existing desktop Host.
