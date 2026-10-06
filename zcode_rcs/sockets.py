import asyncio
import json
import time

from fastapi import WebSocket, WebSocketDisconnect

from .connection import Connection
from .schemas import Auth, Register, Ping, Reply, Detach, desktop_message


def check_origin(ws: WebSocket, config):
    origin = ws.headers.get("origin")
    if origin and origin != config.origin:
        raise PermissionError("ORIGIN_DENIED")


def install_sockets(app, auth, hub, config):
    @app.websocket("/ws/rcs/v1/desktop")
    async def desktop(ws: WebSocket):
        device = None
        connection = None
        try:
            check_origin(ws, config)
            await ws.accept()
            raw = await asyncio.wait_for(ws.receive_text(), 5)
            if len(raw) > 1024:
                raise ValueError("FRAME_TOO_LARGE")
            token = Auth.model_validate_json(raw).token
            session = await auth.resolve(token)
            if session.role != "desktop":
                raise PermissionError("CAPABILITY_DENIED")
            connection = Connection(ws, config.max_queue_bytes)
            raw = await asyncio.wait_for(ws.receive_text(), 5)
            if len(raw) > 2048:
                raise ValueError("FRAME_TOO_LARGE")
            message = Register.model_validate_json(raw)
            device = await hub.register(session, message, connection)
            while True:
                packet = await asyncio.wait_for(ws.receive(), 75)
                if packet["type"] == "websocket.disconnect":
                    break
                if packet.get("bytes") is not None:
                    await hub.forward_device(device, packet["bytes"])
                else:
                    text = packet.get("text", "")
                    if len(text.encode()) > 1024 * 1024:
                        raise ValueError("FRAME_TOO_LARGE")
                    message = desktop_message.validate_json(text)
                    if isinstance(message, Ping):
                        await auth.resolve(session_id=session.id)
                        device.last_seen = time.monotonic()
                        await connection.send({"type": "pong"})
                    elif isinstance(message, Reply):
                        hub.reply(device, message)
                    elif isinstance(message, Detach):
                        attachment = hub.attachments.get(message.attachmentId)
                        if attachment and attachment.device is device:
                            await hub.detach(attachment.id)
                    else:
                        raise ValueError("PROTOCOL_INVALID")
        except (Exception, asyncio.CancelledError):
            if connection:
                await connection.close(1008, "CONNECTION_REJECTED")
            else:
                try:
                    await ws.close(1008)
                except RuntimeError:
                    pass
        finally:
            if device:
                await hub.disconnect(device)

    @app.websocket("/ws/rcs/v1/client")
    async def client(ws: WebSocket):
        connection = None
        attachment = None
        try:
            check_origin(ws, config)
            await ws.accept()
            # ticket 是一次性短期 grant；长期 key/token 绝不进入 URL。
            raw = await asyncio.wait_for(ws.receive_text(), 5)
            if len(raw) > 1024:
                raise ValueError("FRAME_TOO_LARGE")
            message = json.loads(raw)
            if not isinstance(message, dict) or set(message) != {"type", "ticket"} or message["type"] != "ticket" or not isinstance(message["ticket"], str):
                raise ValueError("PROTOCOL_INVALID")
            attachment = await hub.consume_ticket(message["ticket"])
            connection = Connection(ws, config.max_queue_bytes)
            await hub.connect_client(attachment, connection)
            while True:
                packet = await ws.receive()
                if packet["type"] == "websocket.disconnect":
                    break
                if packet.get("bytes") is not None:
                    await hub.forward_client(attachment, packet["bytes"])
                else:
                    if packet.get("text") != '{"type":"ping"}':
                        raise ValueError("PROTOCOL_INVALID")
                    await auth.resolve(session_id=attachment.session.id)
                    await connection.send({"type": "pong"})
        except (Exception, asyncio.CancelledError):
            if connection:
                await connection.close(1008, "CONNECTION_REJECTED")
            else:
                try:
                    await ws.close(1008)
                except RuntimeError:
                    pass
        finally:
            # 被拒绝的第二个 socket 不能释放已有 attachment。
            if attachment and attachment.client is connection:
                await hub.detach(attachment.id)
