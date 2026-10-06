from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

BRIDGE_VERSION = 1
RPC_CODEC_VERSION = 1
AGENT_WIRE_VERSION = 3
MAGIC = b"ZRCS\x01"
HEADER_LENGTH = 25


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Login(Strict):
    key: str = Field(min_length=32, max_length=512)
    role: Literal["client", "desktop"] = "client"
    name: str = Field(default="", max_length=80)


class Auth(Strict):
    type: Literal["auth"]
    token: str = Field(min_length=32, max_length=256)


class Register(Strict):
    type: Literal["register"]
    deviceId: str = Field(min_length=1, max_length=128)
    incarnation: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=80)
    bridgeVersion: Literal[1]
    rpcCodec: Literal[1]
    agentWire: Literal[3]


class Ping(Strict):
    type: Literal["ping"]


class Reply(Strict):
    type: Literal["reply"]
    requestId: str = Field(max_length=128)
    ok: bool
    result: dict | list | None = None
    error: str | None = Field(default=None, max_length=128)


class Detach(Strict):
    type: Literal["detach"]
    attachmentId: str = Field(max_length=128)


DesktopMessage = Annotated[Register | Ping | Reply | Detach, Field(discriminator="type")]
desktop_message = TypeAdapter(DesktopMessage)


class Workspace(Strict):
    handle: str = Field(min_length=1, max_length=128)
    name: str = Field(max_length=256)
    workspacePath: str = Field(max_length=4096)
    workspaceIdentity: str | None = Field(default=None, max_length=4096)
    remoteSessionId: str | None = Field(default=None, max_length=128)


class Host(Strict):
    id: str = Field(min_length=1, max_length=128)
    generation: str = Field(min_length=1, max_length=128)
    name: str = Field(max_length=256)
    workspaces: list[Workspace] = Field(max_length=128)


class Attach(Strict):
    deviceId: str = Field(min_length=1, max_length=128)
    hostId: str = Field(min_length=1, max_length=128)
    hostGeneration: str = Field(min_length=1, max_length=128)
    workspaceHandle: str = Field(min_length=1, max_length=128)


def frame_id(data: bytes, maximum: int) -> str:
    if len(data) < HEADER_LENGTH or len(data) > maximum + HEADER_LENGTH or data[:5] != MAGIC:
        raise ValueError("FRAME_INVALID")
    if int.from_bytes(data[21:25], "big") != len(data) - HEADER_LENGTH:
        raise ValueError("FRAME_INVALID")
    return str(UUID(bytes=data[5:21]))


def make_frame(attachment_id: str, payload: bytes) -> bytes:
    return MAGIC + UUID(attachment_id).bytes + len(payload).to_bytes(4, "big") + payload
