"""PlanGuide 应用服务。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import secrets

from planguide.config import settings
from planguide.domain.plan import PlanTemplate, initial_state, merge_state, summarize_progress
from planguide.infrastructure.excel_import import ExcelImportAdapter
from planguide.infrastructure.security import PasswordHasher


class PlanAuthService:
    def __init__(self, repo):
        self._repo = repo
        self._hasher = PasswordHasher()

    async def register(self, username: str, password: str, invite_code: str) -> dict:
        if invite_code != settings.plan_invite_code:
            raise ValueError("邀请码不正确")
        self._validate_credentials(username, password)
        salt, password_hash = self._hasher.hash_password(password)
        user = await self._repo.create_user(username, password_hash, salt)
        return _user_payload(user)

    async def login(self, username: str, password: str) -> tuple[dict, str, datetime]:
        user = await self._repo.get_user_by_name(username)
        if not user or not self._hasher.verify(password, user["salt"], user["password_hash"]):
            raise ValueError("用户名或密码错误")
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.plan_session_days)
        await self._repo.create_session(user["id"], token, expires_at)
        return _user_payload(user), token, expires_at

    async def current_user(self, token: str | None) -> dict | None:
        if not token:
            return None
        user = await self._repo.get_user_by_session(token)
        return _user_payload(user) if user else None

    async def logout(self, token: str | None):
        if token:
            await self._repo.delete_session(token)

    def _validate_credentials(self, username: str, password: str):
        if len(username.strip()) < 3:
            raise ValueError("用户名至少 3 个字符")
        if len(password) < 6:
            raise ValueError("密码至少 6 个字符")


class PlanTemplateService:
    def __init__(self, repo):
        self._repo = repo

    async def list_templates(self, user_id: int) -> list[dict]:
        await self.ensure_system_templates()
        rows = await self._repo.list_templates(user_id)
        return [_template_summary(row) for row in rows]

    async def get_template(self, user_id: int, template_id: int) -> dict:
        row = await self._repo.get_template_for_user(user_id, template_id)
        if not row:
            raise LookupError("模板不存在")
        return row

    async def ensure_system_templates(self):
        for payload in _load_system_templates():
            await self._repo.upsert_system_template(payload)


class PlanBookshelfService:
    def __init__(self, repo):
        self._repo = repo

    async def list_books(self, user_id: int) -> list[dict]:
        rows = await self._repo.list_instances(user_id)
        return [_instance_summary(row) for row in rows]

    async def create_instance(self, user_id: int, template_id: int, title: str = "") -> dict:
        template_row = await self._repo.get_template_for_user(user_id, template_id)
        if not template_row:
            raise LookupError("模板不存在")
        template = PlanTemplate.model_validate(template_row["template_json"])
        name = title.strip() or template.title
        state = initial_state(template).model_dump()
        row = await self._repo.create_instance(user_id, template_id, name, state)
        return await self.get_instance(user_id, row["id"])

    async def get_instance(self, user_id: int, instance_id: int) -> dict:
        row = await self._repo.get_instance_for_user(user_id, instance_id)
        if not row:
            raise LookupError("计划不存在")
        return _instance_detail(row)

    async def save_state(self, user_id: int, instance_id: int, payload: dict) -> dict:
        row = await self._repo.get_instance_for_user(user_id, instance_id)
        if not row:
            raise LookupError("计划不存在")
        if int(payload.get("revision", -1)) != row["revision"]:
            raise RuntimeError("计划已在其他位置更新")
        state = _merged_state(row, payload.get("state", {}))
        updated = await self._repo.update_state(instance_id, state.model_dump(), row["revision"] + 1)
        return _state_payload(updated)

    async def patch_instance(self, user_id: int, instance_id: int, payload: dict) -> dict:
        row = await self._repo.patch_instance(user_id, instance_id, payload)
        if not row:
            raise LookupError("计划不存在")
        return _instance_summary(row)


class PlanImportService:
    def __init__(self, repo):
        self._repo = repo
        self._excel = ExcelImportAdapter()

    async def preview_excel(self, user_id: int, filename: str, content: bytes) -> dict:
        preview = self._excel.preview(filename, content)
        job = await self._repo.create_import_job(user_id, filename, preview)
        return {"job_id": job["id"], "preview": preview}

    async def confirm_excel(self, user_id: int, payload: dict) -> dict:
        job = await self._repo.get_import_job_for_user(user_id, int(payload.get("job_id", 0)))
        if not job:
            raise LookupError("导入任务不存在")
        template = self._excel.build_template(job["preview_json"], payload)
        row = await self._repo.create_private_template(user_id, template.model_dump())
        await self._repo.mark_import_confirmed(job["id"], payload, row["id"])
        return _template_summary(row)


def build_services(repo) -> dict[str, Any]:
    return {
        "auth": PlanAuthService(repo),
        "templates": PlanTemplateService(repo),
        "bookshelf": PlanBookshelfService(repo),
        "imports": PlanImportService(repo),
    }


def _load_system_templates() -> list[dict]:
    root = Path(__file__).resolve().parents[1] / "templates"
    return [PlanTemplate.model_validate_json(p.read_text(encoding="utf-8")).model_dump() for p in root.glob("*.json")]


def _user_payload(user: dict) -> dict:
    return {"id": user["id"], "username": user["username"]}


def _template_summary(row: dict) -> dict:
    template = row["template_json"]
    return {
        "id": row["id"],
        "title": row["title"],
        "description": template.get("description", ""),
        "source_type": row["source_type"],
        "is_system": row["is_system"],
        "version": row["version"],
    }


def _instance_summary(row: dict) -> dict:
    template = PlanTemplate.model_validate(row["template_json"])
    state = merge_state(template, row["state_json"])
    return {
        "id": row["id"],
        "title": row["title"],
        "status": row["status"],
        "template_title": row["template_title"],
        "source_type": row["source_type"],
        "updated_at": row["updated_at"],
        "progress": summarize_progress(template, state),
    }


def _instance_detail(row: dict) -> dict:
    detail = _instance_summary(row)
    detail["template"] = row["template_json"]
    detail["state"] = row["state_json"]
    detail["revision"] = row["revision"]
    return detail


def _merged_state(row: dict, incoming: dict):
    template = PlanTemplate.model_validate(row["template_json"])
    return merge_state(template, incoming)


def _state_payload(row: dict) -> dict:
    return {
        "state": row["state_json"],
        "revision": row["revision"],
        "updated_at": row["updated_at"],
    }
