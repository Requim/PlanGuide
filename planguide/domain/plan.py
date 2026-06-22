"""计划模板、实例状态和进度统计。"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class PlanField(BaseModel):
    """模板可编辑字段定义，前端按该 schema 渲染控件。"""

    key: str
    label: str
    field_type: str = "text"
    options: list[str] = Field(default_factory=list)
    default: Any = None


class PlanItem(BaseModel):
    item_id: str
    title: str
    detail: str = ""
    date: str = ""
    group: str = ""
    module: str = ""
    output: str = ""


class PlanSection(BaseModel):
    key: str
    title: str
    section_type: str = "items"
    items: list[dict[str, Any]] = Field(default_factory=list)


class PlanTemplate(BaseModel):
    """运行态唯一模板格式，Excel 导入也会转换成该结构。"""

    template_id: str
    version: str = "1.0.0"
    title: str
    description: str = ""
    source_type: str = "json"
    sections: list[PlanSection] = Field(default_factory=list)
    items: list[PlanItem] = Field(default_factory=list)
    fields: list[PlanField] = Field(default_factory=list)


class PlanState(BaseModel):
    item_state: dict[str, dict[str, Any]] = Field(default_factory=dict)
    notes: dict[str, Any] = Field(default_factory=dict)
    records: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


def default_fields() -> list[PlanField]:
    return [
        PlanField(
            key="status",
            label="状态",
            field_type="select",
            options=["未开始", "进行中", "已完成", "需补做"],
            default="未开始",
        ),
        PlanField(key="hours", label="实际用时", field_type="number", default=0),
        PlanField(key="note", label="备注", field_type="textarea", default=""),
    ]


def initial_state(template: PlanTemplate) -> PlanState:
    rows = {item.item_id: _field_defaults(template.fields) for item in template.items}
    return PlanState(item_state=rows)


def merge_state(template: PlanTemplate, incoming: dict[str, Any]) -> PlanState:
    state = PlanState.model_validate(incoming or {})
    for item_id, defaults in initial_state(template).item_state.items():
        state.item_state.setdefault(item_id, defaults)
    return state


def summarize_progress(template: PlanTemplate, state: PlanState) -> dict[str, Any]:
    total = len(template.items)
    done = _count_status(state, "已完成")
    pending = _count_status(state, "需补做")
    today_total, today_done = _today_counts(template, state)
    return {
        "total_items": total,
        "done_items": done,
        "pending_items": pending,
        "completion_rate": round(done / total, 4) if total else 0,
        "today_total": today_total,
        "today_done": today_done,
    }


def _field_defaults(fields: list[PlanField]) -> dict[str, Any]:
    return {field.key: field.default for field in fields}


def _count_status(state: PlanState, status: str) -> int:
    return sum(1 for row in state.item_state.values() if row.get("status") == status)


def _today_counts(template: PlanTemplate, state: PlanState) -> tuple[int, int]:
    today = date.today().isoformat()
    items = [item for item in template.items if item.date == today]
    done = sum(1 for item in items if state.item_state.get(item.item_id, {}).get("status") == "已完成")
    return len(items), done
