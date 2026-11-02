from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

MSG_DATE_REQUIRED = "Enter the judgment date"
MSG_DATE_INCOMPLETE = "Enter the full judgment date"
MSG_DATE_INVALID = "Enter a real date"


class GovukDateParseError(ValueError):
    pass


def parse_govuk_date_from_post(data: Mapping[str, str], name_prefix: str) -> date:
    day = data.get(f"{name_prefix}-day", "").strip()
    month = data.get(f"{name_prefix}-month", "").strip()
    year = data.get(f"{name_prefix}-year", "").strip()

    if not day and not month and not year:
        raise GovukDateParseError(MSG_DATE_REQUIRED)

    if not day or not month or not year:
        raise GovukDateParseError(MSG_DATE_INCOMPLETE)

    try:
        return date(int(year), int(month), int(day))
    except ValueError as error:
        raise GovukDateParseError(MSG_DATE_INVALID) from error
