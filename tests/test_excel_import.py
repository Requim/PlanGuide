from io import BytesIO

from openpyxl import Workbook

from planguide.infrastructure.excel_import import ExcelImportAdapter


def _xlsx_bytes():
    wb = Workbook()
    ws = wb.active
    ws.title = "计划"
    ws.append(["日期", "模块", "主题", "任务", "输出"])
    ws.append(["2026-06-22", "职测", "判断推理", "做 20 题", "错题 3 条"])
    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue()


def test_excel_preview_lists_headers():
    preview = ExcelImportAdapter().preview("plan.xlsx", _xlsx_bytes())
    assert preview["sheets"][0]["headers"][:3] == ["日期", "模块", "主题"]
    assert preview["sheets"][0]["sample_rows"][0][3] == "做 20 题"


def test_excel_confirm_builds_template():
    adapter = ExcelImportAdapter()
    preview = adapter.preview("plan.xlsx", _xlsx_bytes())
    template = adapter.build_template(preview, {
        "title": "导入模板",
        "sheet_name": "计划",
        "mapping": {"date": "日期", "module": "模块", "title": "主题", "detail": "任务", "output": "输出"},
    })
    assert template.source_type == "excel"
    assert template.items[0].title == "判断推理"
    assert template.items[0].detail == "做 20 题"


def test_excel_confirm_requires_title_mapping():
    adapter = ExcelImportAdapter()
    preview = adapter.preview("plan.xlsx", _xlsx_bytes())
    try:
        adapter.build_template(preview, {"sheet_name": "计划", "mapping": {}})
    except ValueError as exc:
        assert "任务标题" in str(exc)
    else:
        raise AssertionError("missing title mapping should fail")
