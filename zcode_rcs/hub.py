import asyncio
import secrets
import time
from dataclasses import dataclass, field
from uuid import uuid4

from pydantic import TypeAdapter

from .auth import AuthStore, Session
from .connection import Connection
from .schemas import Attach, Host, Register, Reply, frame_id


@dataclass(eq=False)
class Device:
    session: Session
    id: str
    incarnation: str
    name: str
    connection: Connection
    pending: dict[str, asyncio.Future] = field(default_factory=dict)
    last_seen: float = field(default_factory=time.monotonic)


@dataclass(eq=False)
class Attachment:
    id: str
    session: Session
    device: Device
    host: Host
    workspace_handle: str
    capabilities: dict
    client: Connection | None = None


class Hub:
    def __init__(self, auth: AuthStore):
        self.auth = auth
        self.config = auth.config
        self.devices: dict[tuple[str, str], Device] = {}
        self.attachments: dict[str, Attachment] = {}
        self.tickets: dict[str, tuple[str, str, float]] = {}

    async def register(self, session: Session, message: Register, connection: Connection):
        key = (session.identity, message.deviceId)
        old = self.devices.get(key)
        if not old and len(self.devices) >= self.config.max_devices:
            raise PermissionError("DEVICE_LIMIT")
        if old:
            await self.disconnect(old, "DEVICE_REPLACED")
        device = Device(session, message.deviceId, message.incarnation, message.name, connection)
        self.devices[key] = device
        await connection.send({"type": "registered", "deviceId": device.id, "incarnation": device.incarnation, "serverInstanceId": self.auth.instance_id})
        return device

    def device(self, session: Session, device_id: str):
        device = self.devices.get((session.identity, device_id))
        if not device or device.connection.closed:
            raise LookupError("DEVICE_OFFLINE")
        return device

    async def request(self, device: Device, kind: str, **params):
        if len(device.pending) >= 64:
            raise ConnectionError("FLOW_SATURATED")
        request_id = secrets.token_hex(16)
        future = asyncio.get_running_loop().create_future()
        device.pending[request_id] = future
        try:
            await device.connection.send({"type": kind, "requestId": request_id, **params})
            return await asyncio.wait_for(future, 20)
        finally:
            device.pending.pop(request_id, None)

    def reply(self, device: Device, reply: Reply):
        future = device.pending.get(reply.requestId)
        if not future or future.done():
            return
        if reply.ok:
            future.set_result(reply.result)
        else:
            future.set_exception(LookupError(reply.error or "HOST_GONE"))

    async def hosts(self, session: Session, device_id: str):
        device = self.device(session, device_id)
        result = await self.request(device, "hosts")
        return TypeAdapter(list[Host]).validate_python(result)

    async def attach(self, session: Session, params: Attach):
        if session.role != "client":
            raise PermissionError("CAPABILITY_DENIED")
        if len(self.attachments) >= self.config.max_attachments:
            raise ConnectionError("ATTACHMENT_LIMIT")
        device = self.device(session, params.deviceId)
        hosts = await self.hosts(session, params.deviceId)
        host = next((h for h in hosts if h.id == params.hostId and h.generation == params.hostGeneration), None)
        if not host or not any(w.handle == params.workspaceHandle for w in host.workspaces):
            raise PermissionError("WORKSPACE_SCOPE_STALE")
        attachment_id = str(uuid4())
        # 先建立传输路由才能接收 Host 的 Initialize，ready 仍等待实际 expose 屏障。
        attachment = Attachment(attachment_id, session, device, host, params.workspaceHandle, {})
        self.attachments[attachment_id] = attachment
        try:
            result = await self.request(device, "attach", attachmentId=attachment_id, hostId=host.id, hostGeneration=host.generation, workspaceHandle=params.workspaceHandle)
            if self.attachments.get(attachment_id) is not attachment or self.devices.get((session.identity, device.id)) is not device:
                raise LookupError("HOST_GONE")
            if not isinstance(result, dict) or not isinstance(result.get("capabilities"), dict):
                raise ValueError("CAPABILITY_MANIFEST_INVALID")
            attachment.capabilities = result["capabilities"]
            return attachment
        except BaseException:
            await self.detach(attachment_id)
            raise

    def owned_attachment(self, session: Session, attachment_id: str):
        attachment = self.attachments.get(attachment_id)
        if not attachment or attachment.session.id != session.id:
            raise PermissionError("CAPABILITY_DENIED")
        return attachment

    def create_ticket(self, session: Session, attachment_id: str):
        self.owned_attachment(session, attachment_id)
        now = time.monotonic()
        self.tickets = {k: v for k, v in self.tickets.items() if v[2] > now}
        if len(self.tickets) >= 128:
            raise PermissionError("TICKET_LIMIT")
        ticket = secrets.token_urlsafe(32)
        self.tickets[ticket] = (session.id, attachment_id, now + 30)
        return ticket

    async def consume_ticket(self, ticket: str):
        entry = self.tickets.pop(ticket, None)
        if not entry or entry[2] < time.monotonic():
            raise PermissionError("AUTH_FAILED")
        session = await self.auth.resolve(session_id=entry[0])
        return self.owned_attachment(session, entry[1])

    async def connect_client(self, attachment: Attachment, connection: Connection):
        if attachment.client:
            raise PermissionError("ATTACHMENT_IN_USE")
        attachment.client = connection
        async def flow(state):
            if self.attachments.get(attachment.id) is attachment:
                await attachment.device.connection.send({"type": "flow", "attachmentId": attachment.id, "state": state})
        connection.on_watermark = flow
        await attachment.device.connection.send({"type": "activate", "attachmentId": attachment.id})

    async def forward_client(self, attachment: Attachment, data: bytes):
        if self.attachments.get(attachment.id) is not attachment or frame_id(data, self.config.max_frame_bytes) != attachment.id:
            raise PermissionError("CAPABILITY_DENIED")
        await attachment.device.connection.send(data)

    async def forward_device(self, device: Device, data: bytes):
        attachment_id = frame_id(data, self.config.max_frame_bytes)
        attachment = self.attachments.get(attachment_id)
        if not attachment or attachment.device is not device:
            raise PermissionError("CAPABILITY_DENIED")
        if not attachment.client:
            raise ConnectionError("ATTACHMENT_NOT_ACTIVE")
        await attachment.client.send(data)

    async def detach(self, attachment_id: str):
        attachment = self.attachments.pop(attachment_id, None)
        if not attachment:
            return
        if attachment.client:
            await attachment.client.close(1000, "ATTACHMENT_CLOSED")
        if not attachment.device.connection.closed:
            try:
                await attachment.device.connection.send({"type": "detach", "attachmentId": attachment_id})
            except ConnectionError:
                pass
        self.tickets = {k: v for k, v in self.tickets.items() if v[1] != attachment_id}

    async def disconnect(self, device: Device, reason="DEVICE_OFFLINE"):
        key = (device.session.identity, device.id)
        if self.devices.get(key) is device:
            self.devices.pop(key, None)
        for attachment in list(self.attachments.values()):
            if attachment.device is device:
                await self.detach(attachment.id)
        for future in device.pending.values():
            if not future.done():
                future.set_exception(ConnectionError(reason))
        await device.connection.close(1000, reason)

    async def revoke(self, session_id: str):
        await self.auth.revoke(session_id)
        for attachment in list(self.attachments.values()):
            if attachment.session.id == session_id:
                await self.detach(attachment.id)
        for device in list(self.devices.values()):
            if device.session.id == session_id:
                await self.disconnect(device, "SESSION_REVOKED")

    async def sweep(self):
        await self.auth.reload_keys()
        for device in list(self.devices.values()):
            try:
                await self.auth.resolve(session_id=device.session.id)
                if time.monotonic() - device.last_seen > 75:
                    raise PermissionError("HEARTBEAT_TIMEOUT")
            except PermissionError:
                await self.disconnect(device, "SESSION_REVOKED")
        for attachment in list(self.attachments.values()):
            try:
                await self.auth.resolve(session_id=attachment.session.id)
            except PermissionError:
                await self.detach(attachment.id)

    async def close(self):
        for device in list(self.devices.values()):
            await self.disconnect(device, "SERVER_SHUTDOWN")
