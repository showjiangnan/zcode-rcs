# Public API and SDK / 公共接口

## Control plane

Prefix `/api/rcs/v1`; errors have `{ "error": { "code": "..." } }`. `/meta` and `/health` are public. Other endpoints require a derived session. Browser authentication uses an HttpOnly/SameSite=Strict cookie and exact Origin checks. Independent clients use `Authorization: Bearer <session token>`. Tokens and bridge keys must never be placed in URLs.

| Method/path | Request / result |
| --- | --- |
| GET `/meta` | bridgeVersion, rpcCodec, agentWire, serverInstanceId, version |
| POST `/auth/session` | `{key,role:"client",name}` → short-term token/id/expiresAt |
| GET `/auth/session` | current role/id/expiresAt |
| POST `/auth/refresh` | sliding renewal, expiresAt |
| DELETE `/auth/session` | revoke session and every attachment/socket it owns |
| GET `/devices` | online devices belonging to the same key identity |
| GET `/devices/{deviceId}/hosts` | live Host generations and explicitly allowed workspace handles |
| POST `/attachments` | `{deviceId,hostId,hostGeneration,workspaceHandle}` → attachment/capabilities |
| GET/DELETE `/attachments/{id}` | current owned attachment / detach |
| POST `/attachments/{id}/socket-ticket` | single-use 30-second ticket |
| GET `/attachments/{id}/resource?path=...` | authenticated active attachment; single HTTP byte range; Host checks path |
| GET `/clients` | sessions in this key identity, no token or key |
| DELETE `/clients/{id}` | revoke selected client and its live connections |

`/openapi.json` provides request schemas. `protocol/` contains both control directions, host/workspace/grant schemas, request/subscription schemas and the full explicit service/method/event allowlist. Method arguments and results use the existing ZCode service/V4 contracts in the desktop repository; the relay does not invent new task semantics.

## Standalone JavaScript SDK

Import `sdk/index.js` directly, or install the `sdk/` directory as a local package. It has no workspace imports and requires no DOM or Electron. `index.d.ts` restricts published service/method/event names; result `T` and method arguments are provided by the integration. Arguments still undergo Host/runtime validation. Inject a standards-compatible `fetch`, `AbortController`, WebSocket adapter and optional clock/cancellation signal for an app environment that lacks those globals. `examples/client.mjs` runs in Node 24 using its native WebSocket.

```js
import { RcsHttpClient, RcsRpcConnection } from './sdk/index.js';
const http = new RcsHttpClient({ endpoint: process.env.RCS_ENDPOINT });
await http.login(process.env.RCS_KEY, 'My client');
const [device] = await http.listDevices();
const [host] = await http.listHosts(device.id);
const [workspace] = host.workspaces;
const attachment = await http.attach({ deviceId: device.id, hostId: host.id,
  hostGeneration: host.generation, workspaceHandle: workspace.handle });
const rpc = await RcsRpcConnection.connect(http, attachment);
const result = await rpc.call({ service: 'file', method: 'readdir',
  args: [{ path: workspace.workspacePath }] });
```

Desktop/model credentials are not returned by configuration read APIs. Empty secret fields in a remote provider save preserve the original desktop value; a replacement is write-only. Clear existing secrets on desktop. The bridge identity grants powerful task and terminal control, so this is not a filesystem sandbox for model-generated shell commands.

### Model configuration APIs (introduced in SDK 1.1.0)

The paired Web 3.14.7 uses two additional `provider-settings` methods. Both are present in the shipped manifest and SDK declarations, and must also be granted by the attached desktop. An older desktop cannot gain a method merely by updating its browser.

```js
// IDs refer to a provider/model already configured on the execution computer.
const discovered = await rpc.call({ service: 'provider-settings',
  method: 'discoverModels', args: [providerId] }); // { view, addedCount }
const view = await rpc.call({ service: 'provider-settings',
  method: 'setPersonalModelFastMode', args: [providerId, modelId, true] });
```

Discovery and configuration are performed by the existing Host service. Model requests and credentials remain on the execution computer. `protocol/v4.schema.json` also includes `toolResultDisplaySchema` and the `node_repl_images` tool-output display variant, so integrators can preserve images alongside text rather than discarding an unfamiliar display. These additions do not grant native computer-control permissions to a browser client.

## Conversations, attachments and recovery

1. Call `zcode-agent.helloConversationV4` then `initializeConversationV4` with `{kind:"clientHello",protocolVersion:3,clientId,clientKind:"web",appVersion,capabilities}`. Keep a stable client ID for the logical client. Only negotiate capabilities announced by Hello.
2. Use `zcode-task.createTask` to create a task through the existing Host service; it returns the real session/task identity. The workspace grant is enforced by Host.
3. Subscribe to `zcode-agent.onDynamicConversationFrame` and use `subscribeConversationV4`. Topic snapshots/chunks/deltas are the existing replayable V4 protocol. Preserve logEpoch/sequence and resync on a gap. Wire frame assembly must complete before applying a chunked snapshot. The shipped Web already implements this.
4. Submit commands using `sendConversationCommandV4`, with a stable commandId, clientId, sessionId, expected log epoch/cursors and the existing command envelope. Do not generate a new commandId after an unknown ACK. Query `queryConversationCommandsV4` and retry the same payload/key only when its result permits it.
5. New text uses `sendText` admission values start-now/queue/steer at the existing runtime boundary; permission/elicitation/plan responses use original interaction IDs. Runtime rejects stale responses. Never use a bridge-side queue to simulate acceptance.
6. Upload attachments using `attachmentBeginV4`, bounded `attachmentChunkV4`, `attachmentCommitV4`; cancel with `attachmentAbortV4`. Receive the runtime ref, not a cloud storage URL. Artifact reads and `conversationRowsRangeV4` fetch persistent details from the same session.
7. On close, discard the old proxy, rediscover the live Host generation/workspace, create a new attachment and handshake/subscribe/resync again. Keep command IDs and cursors in the client, never the relay. Do not send new commands while disconnected.

The SDK provides transport and codec, not a second conversation reducer. Full V4 types and reducers live in `packages/shared/src/zcode-protocol-v4` and `packages/ui/src/v4`. Reuse those contracts when implementing another front end. A mini-program may adapt WebSocket callbacks to `RcsSocket`; binary ArrayBuffer support is mandatory. No WeChat login is required by this API.

## Binary data plane

Connect to `/ws/rcs/v1/client`, send `{type:"ticket",ticket}` as the first text message, then binary frames. Tickets never go in query strings. Bare RPC messages are framed as: 5-byte `ZRCS` + version byte 1, 16-byte attachment UUID, 4-byte big-endian payload length, then the exact codec payload. Total header length is 25 bytes. Maximum payload is 16 MiB; bounded connection output is 32 MiB/512 queued frames. The relay verifies ownership/framing without decoding task RPC payloads. The SDK preserves top-level `Uint8Array` results.

## Resources and terminals

Resources require an active attachment and the same authenticated session. Cookie browsers can use `resourceUrl` for media; bearer integrations should use `readResource`. Each block is at most 512 KiB and file size/mtime is checked while reading. HTML/SVG and other active content is downloaded rather than executed in the bridge origin. There is no permanent public file link.

Terminal `list` discovers only allowed workspace PTYs; call it before `attach` or terminal event subscription. Subscribe to `onDynamicReplayData(id)` first, then `attach({id,afterSequence})`. Merge replay and live chunks by sequence; `truncated` means the 1 MiB output window no longer contains the complete history. Disconnect/detach does not kill a PTY. Explicit `dispose` closes it. Multiple clients share a PTY; the latest explicit resize wins. Keep your own terminal tab mapping; do not close shared terminals merely because a client is offline.

## Errors

- `AUTH_FAILED`, `AUTH_REQUIRED`, `SESSION_EXPIRED`, `KEY_REVOKED`: stop retries and authenticate again.
- `VERSION_INCOMPATIBLE`: update a compatible desktop/Web/SDK bundle.
- `DEVICE_OFFLINE`, `WORKSPACE_OFFLINE`, `HOST_GONE`, `HOST_STALE`, `WORKSPACE_SCOPE_STALE`: rediscover; no automatic remote-to-local fallback.
- `CAPABILITY_DENIED`: method/path/workspace/session/terminal is outside the grant.
- `FLOW_SATURATED`, socket 1013: reconnect and resync from runtime facts.
- `RESOURCE_CHANGED`: source file was edited during reading; begin a fresh request.
- V4 rejected/stale/unknown ACKs retain their original runtime semantics.

## Workflow companion methods

The public `zcode-agent` service adds `syncDynamicWorkflowUserMode`, `findSavedWorkflowForRun`, and `saveSavedWorkflowFromRun`. They use the existing Host, persisted settings and workspace checks. Native sandbox registration, MCP page sampling and page-tool registration remain absent from the public manifest.
# ChatGPT 订阅连接

`chatgpt-subscription.execute` 在已配对 Desktop Host 上支持只读状态和目录刷新：

```json
{"service":"chatgpt-subscription","method":"execute","args":[{"type":"read"}]}
```

刷新使用同一请求结构，命令为 `{"type":"refresh-models"}`。结果包含可用性、当前连接标签、授权状态和模型目录，不含原始令牌或本机推理 capability。

登录、切换、重新授权、订阅用量确认、退出和移除连接必须在本机 Desktop 设置页进行；远程发起这些命令会被拒绝。Web 选择已经连接的订阅模型，仍由原 Desktop runtime 执行，不向桥接服务器发送 OAuth 凭据。独立 SSH/Docker 的未装配执行端不自动复制桌面授权，也不会转到另一个收费模型。
