import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .auth import AuthStore
from .config import Config, from_env
from .http_api import create_api, PREFIX
from .hub import Hub
from .schemas import Login
from .sockets import install_sockets


def create_app(config: Config | None = None):
    config = (config or from_env()).validate()
    auth = AuthStore(config)
    hub = Hub(auth)

    async def sweep():
        while True:
            await asyncio.sleep(10)
            try:
                await hub.sweep()
            except (OSError, ValueError):
                # 配置更新写入失败时保留已校验版本，不记录配置或凭据正文。
                pass

    @asynccontextmanager
    async def lifespan(app):
        await auth.initialize()
        task = asyncio.create_task(sweep())
        yield
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await hub.close()

    app = FastAPI(title="ZCode RCS", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.auth = auth
    app.state.hub = hub

    @app.exception_handler(PermissionError)
    async def permission_error(request, error):
        code = str(error)
        status = 429 if code.endswith("LIMITED") else 403 if code in {"CAPABILITY_DENIED", "ORIGIN_DENIED", "WORKSPACE_SCOPE_STALE"} else 401
        return JSONResponse({"error": {"code": code}}, status_code=status)

    @app.exception_handler(LookupError)
    @app.exception_handler(ConnectionError)
    @app.exception_handler(TimeoutError)
    async def transport_error(request, error):
        return JSONResponse({"error": {"code": str(error) or "DEVICE_TIMEOUT"}}, status_code=503)

    @app.middleware("http")
    async def secure_response(request: Request, call_next):
        length = request.headers.get("content-length", "0")
        if not length.isdigit() or int(length) > 65536:
            return JSONResponse({"error": {"code": "FRAME_TOO_LARGE"}}, status_code=413)
        # 同源 cookie 与 websocket 使用相同 Origin；不启用全域 credential CORS。
        origin = request.headers.get("origin")
        if origin and origin != config.origin:
            return JSONResponse({"error": {"code": "ORIGIN_DENIED"}}, status_code=403)
        if request.method in {"POST", "PUT", "PATCH"}:
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 65536:
                    return JSONResponse({"error": {"code": "FRAME_TOO_LARGE"}}, status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api") else "no-cache"
        return response

    @app.post(PREFIX + "/auth/session")
    async def login(params: Login, request: Request, response: Response):
        auth.rate_limit(request.client.host if request.client else "unknown")
        session, token = await auth.login(params.key, params.role, params.name)
        response.set_cookie("zcode_rcs", token, httponly=True, secure=config.origin.startswith("https:"), samesite="strict", max_age=30 * 86400, path="/")
        return {"token": token, "id": session.id, "expiresAt": session.expires}

    app.include_router(create_api(auth, hub, config))
    install_sockets(app, auth, hub, config)

    if config.web_dir.is_dir():
        if (config.web_dir / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=config.web_dir / "assets"), name="assets")
        @app.get("/{path:path}")
        async def frontend(path: str):
            root = config.web_dir.resolve()
            candidate = (root / path).resolve()
            if candidate.is_relative_to(root) and candidate.is_file():
                return FileResponse(candidate)
            if path.startswith(("api/", "ws/")):
                return JSONResponse({"error": {"code": "NOT_FOUND"}}, status_code=404)
            return FileResponse(root / "index.html")
    return app
