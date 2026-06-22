"""计划系统仓储。"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from planguide.infrastructure.models import (
    PlanImportJobModel,
    PlanInstanceModel,
    PlanSessionModel,
    PlanStateModel,
    PlanTemplateModel,
    PlanUserModel,
)
from planguide.infrastructure.security import PasswordHasher


class PlanRepository:
    def __init__(self, session_factory: async_sessionmaker):
        self._sf = session_factory
        self._security = PasswordHasher()

    async def create_user(self, username: str, password_hash: str, salt: str) -> dict:
        async with self._sf() as sess:
            if await self._username_exists(sess, username):
                raise ValueError("用户名已存在")
            row = PlanUserModel(username=username, password_hash=password_hash, salt=salt)
            sess.add(row)
            await sess.commit()
            await sess.refresh(row)
            return _user(row)

    async def get_user_by_name(self, username: str) -> dict | None:
        async with self._sf() as sess:
            stmt = select(PlanUserModel).where(PlanUserModel.username == username)
            row = (await sess.execute(stmt)).scalar_one_or_none()
            return _user(row) if row else None

    async def create_session(self, user_id: int, token: str, expires_at: datetime):
        async with self._sf() as sess:
            sess.add(PlanSessionModel(
                user_id=user_id,
                token_hash=self._security.hash_token(token),
                expires_at=expires_at,
            ))
            await sess.commit()

    async def get_user_by_session(self, token: str) -> dict | None:
        async with self._sf() as sess:
            stmt = _session_select(self._security.hash_token(token))
            result = (await sess.execute(stmt)).first()
            if not result or _as_utc(result[0].expires_at) < datetime.now(timezone.utc):
                return None
            return _user(result[1])

    async def delete_session(self, token: str):
        async with self._sf() as sess:
            row = await self._session_by_token(sess, token)
            if row:
                await sess.delete(row)
                await sess.commit()

    async def list_templates(self, user_id: int) -> list[dict]:
        async with self._sf() as sess:
            stmt = select(PlanTemplateModel).where(
                (PlanTemplateModel.is_system == 1) | (PlanTemplateModel.owner_user_id == user_id)
            )
            rows = (await sess.execute(stmt.order_by(PlanTemplateModel.created_at))).scalars().all()
            return [_template(row) for row in rows]

    async def get_template_for_user(self, user_id: int, template_id: int) -> dict | None:
        async with self._sf() as sess:
            row = await sess.get(PlanTemplateModel, template_id)
            return _template(row) if row and _can_access_template(row, user_id) else None

    async def upsert_system_template(self, payload: dict):
        async with self._sf() as sess:
            stmt = select(PlanTemplateModel).where(PlanTemplateModel.template_key == payload["template_id"])
            row = (await sess.execute(stmt)).scalar_one_or_none()
            await self._save_template(sess, row, payload, None, True)

    async def create_private_template(self, user_id: int, payload: dict) -> dict:
        async with self._sf() as sess:
            row = await self._save_template(sess, None, payload, user_id, False)
            return _template(row)

    async def create_instance(self, user_id: int, template_id: int, title: str, state: dict) -> dict:
        async with self._sf() as sess:
            row = PlanInstanceModel(user_id=user_id, template_id=template_id, title=title)
            sess.add(row)
            await sess.flush()
            sess.add(PlanStateModel(instance_id=row.id, state_json=state))
            await sess.commit()
            return {"id": row.id}

    async def list_instances(self, user_id: int) -> list[dict]:
        async with self._sf() as sess:
            stmt = _instance_select().where(PlanInstanceModel.user_id == user_id)
            rows = (await sess.execute(stmt.order_by(PlanInstanceModel.updated_at.desc()))).all()
            return [_instance(*row) for row in rows]

    async def get_instance_for_user(self, user_id: int, instance_id: int) -> dict | None:
        async with self._sf() as sess:
            stmt = _instance_select().where(PlanInstanceModel.id == instance_id, PlanInstanceModel.user_id == user_id)
            row = (await sess.execute(stmt)).first()
            return _instance(*row) if row else None

    async def update_state(self, instance_id: int, state: dict, revision: int) -> dict:
        async with self._sf() as sess:
            row = await sess.get(PlanStateModel, instance_id)
            row.state_json = state
            row.revision = revision
            row.updated_at = datetime.now()
            await _touch_instance(sess, instance_id, row.updated_at)
            await sess.commit()
            return _state(row)

    async def patch_instance(self, user_id: int, instance_id: int, payload: dict) -> dict | None:
        async with self._sf() as sess:
            row = await sess.get(PlanInstanceModel, instance_id)
            if row is None or row.user_id != user_id:
                return None
            _patch_instance(row, payload)
            await sess.commit()
        return await self.get_instance_for_user(user_id, instance_id)

    async def create_import_job(self, user_id: int, filename: str, preview: dict) -> dict:
        async with self._sf() as sess:
            row = PlanImportJobModel(user_id=user_id, filename=filename, preview_json=preview)
            sess.add(row)
            await sess.commit()
            await sess.refresh(row)
            return {"id": row.id}

    async def get_import_job_for_user(self, user_id: int, job_id: int) -> dict | None:
        async with self._sf() as sess:
            row = await sess.get(PlanImportJobModel, job_id)
            return _import_job(row) if row and row.user_id == user_id else None

    async def mark_import_confirmed(self, job_id: int, mapping: dict, template_id: int):
        async with self._sf() as sess:
            row = await sess.get(PlanImportJobModel, job_id)
            row.mapping_json = mapping
            row.template_id = template_id
            row.status = "confirmed"
            await sess.commit()

    async def _username_exists(self, sess, username: str) -> bool:
        stmt = select(PlanUserModel.id).where(PlanUserModel.username == username)
        return (await sess.execute(stmt)).first() is not None

    async def _session_by_token(self, sess, token: str):
        stmt = select(PlanSessionModel).where(PlanSessionModel.token_hash == self._security.hash_token(token))
        return (await sess.execute(stmt)).scalar_one_or_none()

    async def _save_template(self, sess, row, payload: dict, user_id: int | None, is_system: bool):
        row = row or PlanTemplateModel(template_key=payload["template_id"])
        row.title = payload["title"]
        row.version = payload.get("version", "1.0.0")
        row.source_type = payload.get("source_type", "json")
        row.owner_user_id = user_id
        row.is_system = 1 if is_system else 0
        row.template_json = payload
        sess.add(row)
        await sess.commit()
        await sess.refresh(row)
        return row


def _session_select(token_hash: str):
    return select(PlanSessionModel, PlanUserModel).join(PlanUserModel).where(PlanSessionModel.token_hash == token_hash)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _instance_select():
    return select(PlanInstanceModel, PlanTemplateModel, PlanStateModel).join(PlanTemplateModel).join(PlanStateModel)


async def _touch_instance(sess, instance_id: int, updated_at: datetime):
    instance = await sess.get(PlanInstanceModel, instance_id)
    instance.updated_at = updated_at


def _can_access_template(row: PlanTemplateModel, user_id: int) -> bool:
    return bool(row.is_system) or row.owner_user_id == user_id


def _patch_instance(row: PlanInstanceModel, payload: dict):
    if "title" in payload:
        row.title = str(payload["title"]).strip() or row.title
    if payload.get("status") in {"active", "archived"}:
        row.status = payload["status"]
    row.updated_at = datetime.now()


def _user(row: PlanUserModel) -> dict:
    return {"id": row.id, "username": row.username, "password_hash": row.password_hash, "salt": row.salt}


def _template(row: PlanTemplateModel) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "template_json": row.template_json,
        "source_type": row.source_type,
        "is_system": bool(row.is_system),
        "version": row.version,
    }


def _instance(instance, template, state) -> dict:
    return {
        "id": instance.id,
        "title": instance.title,
        "status": instance.status,
        "template_title": template.title,
        "source_type": template.source_type,
        "template_json": template.template_json,
        "state_json": state.state_json,
        "revision": state.revision,
        "updated_at": state.updated_at.isoformat(),
    }


def _state(row: PlanStateModel) -> dict:
    return {"state_json": row.state_json, "revision": row.revision, "updated_at": row.updated_at.isoformat()}


def _import_job(row: PlanImportJobModel) -> dict:
    return {"id": row.id, "preview_json": row.preview_json}
