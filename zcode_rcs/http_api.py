import base64
import re
from urllib.parse import quote
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

from . import __version__
from .schemas import Attach, BRIDGE_VERSION, RPC_CODEC_VERSION, AGENT_WIRE_VERSION

PREFIX = "/api/rcs/v1"


def attachment_json(attachment):
    return {"id": attachment.id, "deviceId": attachment.device.id, "hostId": attachment.host.id,
            "hostGeneration": attachment.host.generation, "workspaceHandle": attachment.workspace_handle,
            "capabilities": attachment.capabilities, "state": "connected" if attachment.client else "ready"}


def create_api(auth, hub, config):
    router = APIRouter(prefix=PREFIX)

    async def session(request: Request):
        authorization = request.headers.get("authorization", "")
        bearer = authorization[7:] if authorization.startswith("Bearer ") else ""
        token = bearer or request.cookies.get("zcode_rcs", "")
        if request.method not in {"GET", "HEAD"} and not bearer and request.headers.get("origin") != config.origin:
            raise PermissionError("ORIGIN_DENIED")
        return await auth.resolve(token)

    @router.get("/health")
    async def health():
        return {"status": "ok"}

    @router.get("/meta")
    async def meta():
        return {"serverInstanceId": auth.instance_id, "bridgeVersion": BRIDGE_VERSION,
                "rpcCodec": RPC_CODEC_VERSION, "agentWire": AGENT_WIRE_VERSION, "version": __version__}

    @router.get("/auth/session")
    async def me(request: Request):
        current = await session(request)
        return {"id": current.id, "role": current.role, "expiresAt": current.expires}

    @router.post("/auth/refresh")
    async def refresh(request: Request):
        current = await session(request)
        return {"expiresAt": await auth.refresh(current)}

    @router.delete("/auth/session")
    async def logout(request: Request, response: Response):
        current = await session(request)
        await hub.revoke(current.id)
        response.delete_cookie("zcode_rcs", path="/")
        return {"ok": True}

    @router.get("/devices")
    async def devices(request: Request):
        current = await session(request)
        return [{"id": d.id, "name": d.name, "incarnation": d.incarnation, "online": True}
                for d in hub.devices.values() if d.session.identity == current.identity and not d.connection.closed]

    @router.get("/devices/{device_id}/hosts")
    async def hosts(device_id: str, request: Request):
        return [h.model_dump() for h in await hub.hosts(await session(request), device_id)]

    @router.post("/attachments")
    async def attach(params: Attach, request: Request):
        return attachment_json(await hub.attach(await session(request), params))

    @router.get("/attachments/{attachment_id}")
    async def get_attachment(attachment_id: str, request: Request):
        return attachment_json(hub.owned_attachment(await session(request), attachment_id))

    @router.delete("/attachments/{attachment_id}")
    async def detach(attachment_id: str, request: Request):
        current = await session(request)
        if attachment_id in hub.attachments:
            hub.owned_attachment(current, attachment_id)
        await hub.detach(attachment_id)
        return {"ok": True}

    @router.post("/attachments/{attachment_id}/socket-ticket")
    async def ticket(attachment_id: str, request: Request):
        return {"ticket": hub.create_ticket(await session(request), attachment_id), "expiresIn": 30}

    @router.get("/attachments/{attachment_id}/resource")
    async def resource(attachment_id: str, request: Request, path: str):
        current = await session(request)
        attachment = hub.owned_attachment(current, attachment_id)
        if not attachment.client or not path or len(path) > 4096:
            raise PermissionError("CAPABILITY_DENIED")
        result = await hub.request(attachment.device, "resource", attachmentId=attachment_id, operation="stat", path=path)
        if not isinstance(result, dict) or result.get("type") != "file" or not isinstance(result.get("size"), int):
            raise LookupError("RESOURCE_NOT_FOUND")
        size = result["size"]
        start, end = 0, max(0, size - 1)
        partial = request.headers.get("range")
        if partial:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", partial)
            if not match or not any(match.groups()) or size == 0:
                return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
            left, right = match.groups()
            if left:
                start = int(left); end = min(int(right) if right else size - 1, size - 1)
            else:
                start = max(0, size - int(right)); end = size - 1
            if start > end or start >= size:
                return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
        async def body():
            position = start
            while position <= end and size:
                await auth.resolve(session_id=current.id)
                if hub.owned_attachment(current, attachment_id) is not attachment or not attachment.client:
                    raise PermissionError("CAPABILITY_DENIED")
                length = min(512 * 1024, end + 1 - position)
                value = await hub.request(attachment.device, "resource", attachmentId=attachment_id, operation="read", path=path, offset=position, length=length, expectedSize=size, **({"expectedMtimeMs": result["mtimeMs"]} if "mtimeMs" in result else {}))
                if not isinstance(value, dict) or not isinstance(value.get("dataBase64"), str):
                    raise ValueError("RESOURCE_INVALID")
                data = base64.b64decode(value["dataBase64"], validate=True)
                if len(data) != length:
                    raise IOError("RESOURCE_CHANGED")
                position += len(data)
                yield data
        import mimetypes
        media = mimetypes.guess_type(path)[0] or "application/octet-stream"
        # 活跃内容始终下载，避免工作区 HTML/SVG 在登录 origin 内执行。
        headers = {"Accept-Ranges": "bytes", "Content-Length": str(0 if not size else end + 1 - start), "Cache-Control": "no-store", "Content-Security-Policy": "sandbox"}
        if media not in {"image/png", "image/jpeg", "image/gif", "image/webp", "image/avif", "video/mp4", "video/webm", "audio/mpeg", "audio/wav", "audio/ogg", "application/pdf"}:
            headers["Content-Disposition"] = "attachment; filename*=UTF-8''" + quote(path.replace("\\", "/").split("/")[-1], safe="")
        if partial:
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        return StreamingResponse(body(), status_code=206 if partial else 200, media_type=media, headers=headers)

    @router.get("/clients")
    async def clients(request: Request):
        current = await session(request)
        return await auth.clients(current.identity)

    @router.delete("/clients/{client_id}")
    async def revoke(client_id: str, request: Request):
        current = await session(request)
        clients = await auth.clients(current.identity)
        if not any(client["id"] == client_id for client in clients):
            raise PermissionError("CAPABILITY_DENIED")
        await hub.revoke(client_id)
        return {"ok": True}

    return router
