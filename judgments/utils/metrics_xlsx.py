from collections.abc import Iterable
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet


def _raw(value: dict[str, Any] | None) -> int | float | None:
    return None if value is None else value["raw"]


def _append_rows(worksheet: Worksheet, headers: list[str], rows: Iterable[Iterable[Any]]) -> None:
    worksheet.append(headers)
    for row in rows:
        worksheet.append(list(row))

    for cell in worksheet[1]:
        cell.font = Font(bold=True)
    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    for column in worksheet.columns:
        width = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column)
        worksheet.column_dimensions[column[0].column_letter].width = min(width + 2, 40)


def _add_summary_sheet(workbook: Workbook, context: dict[str, Any]) -> None:
    _append_rows(
        workbook.create_sheet("Summary"),
        ["Metric", "Value"],
        ((metric["label"], metric["value"]) for metric in context["summary_metrics"]),
    )


def _add_lifecycle_sheets(workbook: Workbook, context: dict[str, Any]) -> None:
    for table in context["lifecycle_metrics"]:
        is_first_publication = table["show_within_24_hours_percentage"]
        headers = ["Period", "Documents measured"]
        if is_first_publication:
            headers.extend(
                [
                    "Within 24 hours count",
                    "Within 24 hours percentage",
                ],
            )
        headers.extend(["Median time (seconds)", "Mean time (seconds)"])

        rows = []
        for row in table["rows"]:
            values = [row["period_raw"], row["count"]]
            if is_first_publication:
                percentage = row.get("within_24_hours_percentage")
                values.extend(
                    [
                        None if percentage is None else percentage["numerator"],
                        _raw(percentage),
                    ],
                )
            values.extend([_raw(row.get("median")), _raw(row.get("mean"))])
            rows.append(values)

        sheet_name = "First publication" if is_first_publication else "Latest publication"
        _append_rows(workbook.create_sheet(sheet_name), headers, rows)


def _add_submission_sheet(workbook: Workbook, context: dict[str, Any]) -> None:
    rows = (
        (
            row["period_raw"],
            row["count"],
            row["total"],
            _raw(row.get("median")),
            _raw(row.get("mean")),
        )
        for table in context["submission_metrics"]
        for row in table["rows"]
    )
    _append_rows(
        workbook.create_sheet("Submissions"),
        ["Period", "Documents measured", "Total submissions", "Median submissions", "Mean submissions"],
        rows,
    )


def _add_court_lifecycle_sheet(workbook: Workbook, context: dict[str, Any]) -> None:
    rows = []
    for court in context["court_lifecycle_metrics"]:
        for row in court["rows"]:
            first = row["first_publication"]
            latest = row["latest_publication"]
            percentage = None if first is None else first.get("within_24_hours_percentage")
            rows.append(
                (
                    court["name"],
                    court["type"],
                    row["period_raw"],
                    None if first is None else first["count"],
                    None if percentage is None else percentage["numerator"],
                    _raw(percentage),
                    None if first is None else _raw(first.get("median")),
                    None if first is None else _raw(first.get("mean")),
                    None if latest is None else latest["count"],
                    None if latest is None else _raw(latest.get("median")),
                    None if latest is None else _raw(latest.get("mean")),
                ),
            )

    _append_rows(
        workbook.create_sheet("Court lifecycle"),
        [
            "Court or tribunal",
            "Type",
            "Period",
            "First publication documents measured",
            "First publication within 24 hours count",
            "First publication within 24 hours percentage",
            "First publication median time (seconds)",
            "First publication mean time (seconds)",
            "Latest publication documents measured",
            "Latest publication median time (seconds)",
            "Latest publication mean time (seconds)",
        ],
        rows,
    )


def _add_documents_by_court_sheet(workbook: Workbook, context: dict[str, Any]) -> None:
    _append_rows(
        workbook.create_sheet("Documents by court"),
        ["Court or tribunal", "Type", "Documents"],
        ((row["name"], row["type"], row["document_count"]) for row in context["cases_by_court"]),
    )


def _add_raw_metrics_sheet(workbook: Workbook, context: dict[str, Any]) -> None:
    raw_metrics = context["raw_metrics"]
    value_keys = sorted(
        {key for metric_response in raw_metrics for values in metric_response["response"].values() for key in values},
    )
    rows = []
    for metric_response in raw_metrics:
        response = metric_response["response"]
        if not response:
            rows.append((metric_response["metric"], metric_response["court"], None, *([None] * len(value_keys))))
            continue
        for period, values in sorted(response.items()):
            rows.append(
                (
                    metric_response["metric"],
                    metric_response["court"],
                    period,
                    *(values.get(key) for key in value_keys),
                ),
            )

    _append_rows(
        workbook.create_sheet("Raw metrics"),
        ["Metric", "Court filter", "Period", *value_keys],
        rows,
    )


def build_metrics_workbook(context: dict[str, Any]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)

    _add_summary_sheet(workbook, context)
    _add_lifecycle_sheets(workbook, context)
    _add_submission_sheet(workbook, context)
    _add_court_lifecycle_sheet(workbook, context)
    _add_documents_by_court_sheet(workbook, context)
    _add_raw_metrics_sheet(workbook, context)

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
