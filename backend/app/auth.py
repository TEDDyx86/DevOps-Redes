"""Session guard and authentication routes; monitoring endpoints are independent."""
import asyncio
import hmac
from urllib.parse import urlparse

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth_store import SESSION_SECONDS


COOKIE = "aularedes_session"
PUBLIC_API = {"/api/auth/login", "/api/auth/session", "/api/webhooks/alerts"}


def origin_allowed(request):
    origin = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site":
        return False
    return not origin or origin == f"{request.url.scheme}://{request.headers.get('host')}"


def ip_address(request):
    return request.client.host if request.client else "unknown"


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.@-]+$")
    password: str = Field(min_length=1, max_length=256)


def install_auth(app, settings):
    @app.middleware("http")
    async def guard(request, call_next):
        path = request.url.path
        protected = (path.startswith("/api/") and path not in PUBLIC_API) or path in {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}
        if protected:
            session = await asyncio.to_thread(app.state.auth.session, request.cookies.get(COOKIE, ""))
            if session is None:
                return JSONResponse({"detail": "Entre para acessar o laboratório.", "code": "session_required"}, status_code=401, headers={"Cache-Control": "no-store"})
            request.state.session = session
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                csrf = request.headers.get("x-csrf-token", "")
                if not origin_allowed(request) or not hmac.compare_digest(csrf.encode(), session["csrf_token"].encode()):
                    return JSONResponse({"detail": "Validação de segurança inválida. Atualize a página."}, status_code=403)
        response = await call_next(request)
        if path.startswith("/api/") or protected:
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    router = APIRouter(prefix="/api")

    @router.post("/auth/login")
    def login(body: LoginBody, request: Request):
        if not origin_allowed(request):
            return JSONResponse({"detail": "Origem de acesso não permitida."}, status_code=403)
        result = app.state.auth.login(body.username, body.password, ip_address(request), previous_token=request.cookies.get(COOKIE, ""))
        status = result.pop("status")
        if status != 200:
            messages = {401: "Usuário ou senha inválidos.", 429: f"Muitas tentativas de acesso. Aguarde {result.get('retry_after', 60)} s antes de tentar novamente.", 503: "Acesso não configurado. Execute scripts/configure.py e reinicie a API."}
            headers = {"Retry-After": str(result["retry_after"])} if status == 429 else {}
            return JSONResponse({"detail": messages[status], **result}, status_code=status, headers=headers)
        token = result.pop("token")
        response = JSONResponse(result)
        response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite="strict", secure=settings.auth_cookie_secure, path="/")
        return response

    @router.get("/auth/session")
    def session(request: Request):
        result = app.state.auth.session(request.cookies.get(COOKIE, ""))
        return result if result else JSONResponse({"detail": "Sessão encerrada. Entre novamente."}, status_code=401)

    @router.post("/auth/logout")
    def logout(request: Request):
        app.state.auth.logout(request.cookies.get(COOKIE, ""), request.state.session["username"], ip_address(request))
        response = JSONResponse({"status": "ok"})
        response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict", secure=settings.auth_cookie_secure)
        return response

    @router.get("/security")
    def security():
        return app.state.auth.stats()

    app.include_router(router)
