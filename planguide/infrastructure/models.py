"""SQLAlchemy ORM 表定义。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PlanUserModel(Base):
    __tablename__ = "plan_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    salt: Mapped[str] = mapped_column(String(64))
    disabled: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_login: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PlanSessionModel(Base):
    __tablename__ = "plan_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("plan_user.id"))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PlanTemplateModel(Base):
    __tablename__ = "plan_template"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_key: Mapped[str] = mapped_column(String(96), unique=True)
    title: Mapped[str] = mapped_column(String(128))
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    source_type: Mapped[str] = mapped_column(String(16), default="json")
    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("plan_user.id"), nullable=True)
    is_system: Mapped[int] = mapped_column(Integer, default=0)
    template_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PlanInstanceModel(Base):
    __tablename__ = "plan_instance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("plan_user.id"))
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("plan_template.id"))
    title: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PlanStateModel(Base):
    __tablename__ = "plan_state"

    instance_id: Mapped[int] = mapped_column(Integer, ForeignKey("plan_instance.id"), primary_key=True)
    state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PlanImportJobModel(Base):
    __tablename__ = "plan_import_job"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("plan_user.id"))
    filename: Mapped[str] = mapped_column(String(256))
    preview_json: Mapped[dict] = mapped_column(JSON, default=dict)
    mapping_json: Mapped[dict] = mapped_column(JSON, default=dict)
    template_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("plan_template.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="preview")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
