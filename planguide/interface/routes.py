"""HTTP API 路由。"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

from planguide.config import settings

PLAN_COOKIE = "plan_session"


def create_router(services: dict) -> APIRouter:
    router = APIRouter(prefix="/plan/api", tags=["plan"])

    async def current_user(plan_session: Annotated[str | None, Cookie()] = None):
        user = await services["auth"].current_user(plan_session)
        if not user:
            raise HTTPException(status_code=401, detail="未登录")
        return user

    _register_auth_routes(router, services, current_user)
    _register_template_routes(router, services, current_user)
    _register_instance_routes(router, services, current_user)
    _register_import_routes(router, services, current_user)
    return router


def _register_auth_routes(router: APIRouter, services: dict, current_user):
    @router.post("/auth/register")
    async def register(payload: dict):
        try:
            user = await services["auth"].register(
                payload.get("username", ""),
                payload.get("password", ""),
                payload.get("invite_code", ""),
            )
            return {"user": user}
        except ValueError as exc:
            return _error(str(exc), 400)

    @router.post("/auth/login")
    async def login(payload: dict, response: Response):
        try:
            user, token, expires_at = await services["auth"].login(payload.get("username", ""), payload.get("password", ""))
        except ValueError as exc:
            return _error(str(exc), 401)
        _set_cookie(response, token, expires_at)
        return {"user": user}

    @router.post("/auth/logout")
    async def logout(response: Response, plan_session: Annotated[str | None, Cookie()] = None):
        await services["auth"].logout(plan_session)
        response.delete_cookie(PLAN_COOKIE, path="/plan")
        return {"success": True}

    @router.get("/auth/me")
    async def me(user: dict = Depends(current_user)):
        return {"user": user}


def _register_template_routes(router: APIRouter, services: dict, current_user):
    @router.get("/templates")
    async def templates(user: dict = Depends(current_user)):
        return {"templates": await services["templates"].list_templates(user["id"])}

    @router.get("/templates/{template_id}")
    async def template_detail(template_id: int, user: dict = Depends(current_user)):
        try:
            return await services["templates"].get_template(user["id"], template_id)
        except LookupError as exc:
            return _error(str(exc), 404)


def _register_instance_routes(router: APIRouter, services: dict, current_user):
    @router.get("/bookshelf")
    async def bookshelf(user: dict = Depends(current_user)):
        return {"books": await services["bookshelf"].list_books(user["id"])}

    @router.post("/instances")
    async def create_instance(payload: dict, user: dict = Depends(current_user)):
        try:
            return await services["bookshelf"].create_instance(user["id"], int(payload.get("template_id", 0)), payload.get("title", ""))
        except LookupError as exc:
            return _error(str(exc), 404)

    @router.get("/instances/{instance_id}")
    async def get_instance(instance_id: int, user: dict = Depends(current_user)):
        try:
            return await services["bookshelf"].get_instance(user["id"], instance_id)
        except LookupError as exc:
            return _error(str(exc), 404)

    @router.put("/instances/{instance_id}/state")
    async def save_state(instance_id: int, payload: dict, user: dict = Depends(current_user)):
        try:
            return await services["bookshelf"].save_state(user["id"], instance_id, payload)
        except LookupError as exc:
            return _error(str(exc), 404)
        except RuntimeError as exc:
            return _error(str(exc), 409)

    @router.patch("/instances/{instance_id}")
    async def patch_instance(instance_id: int, payload: dict, user: dict = Depends(current_user)):
        try:
            return await services["bookshelf"].patch_instance(user["id"], instance_id, payload)
        except LookupError as exc:
            return _error(str(exc), 404)


def _register_import_routes(router: APIRouter, services: dict, current_user):
    @router.post("/imports/excel/preview")
    async def excel_preview(file: UploadFile = File(...), user: dict = Depends(current_user)):
        try:
            return await services["imports"].preview_excel(user["id"], file.filename or "", await file.read())
        except ValueError as exc:
            return _error(str(exc), 400)

    @router.post("/imports/excel/confirm")
    async def excel_confirm(payload: dict, user: dict = Depends(current_user)):
        try:
            return await services["imports"].confirm_excel(user["id"], payload)
        except (LookupError, ValueError) as exc:
            return _error(str(exc), 400)


def _set_cookie(response: Response, token: str, expires_at):
    response.set_cookie(
        PLAN_COOKIE,
        token,
        expires=expires_at,
        httponly=True,
        secure=settings.plan_cookie_secure,
        samesite="lax",
        path="/plan",
    )


def _error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status_code)
