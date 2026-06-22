from planguide.domain.plan import PlanItem, PlanTemplate, initial_state, merge_state, summarize_progress, default_fields


def _template():
    return PlanTemplate(
        template_id="unit",
        title="单测",
        fields=default_fields(),
        items=[PlanItem(item_id="a", title="A"), PlanItem(item_id="b", title="B")],
    )


def test_initial_state_creates_rows():
    state = initial_state(_template())
    assert state.item_state["a"]["status"] == "未开始"
    assert state.item_state["b"]["hours"] == 0


def test_merge_state_backfills_missing_rows():
    state = merge_state(_template(), {"item_state": {"a": {"status": "已完成"}}})
    assert state.item_state["a"]["status"] == "已完成"
    assert state.item_state["b"]["status"] == "未开始"


def test_progress_counts_status():
    template = _template()
    state = initial_state(template)
    state.item_state["a"]["status"] = "已完成"
    state.item_state["b"]["status"] = "需补做"
    result = summarize_progress(template, state)
    assert result["done_items"] == 1
    assert result["pending_items"] == 1
    assert result["completion_rate"] == 0.5
