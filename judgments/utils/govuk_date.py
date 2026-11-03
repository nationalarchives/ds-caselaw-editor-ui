from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

MSG_DATE_REQUIRED = "Enter the judgment date"
MSG_DATE_INCOMPLETE = "Enter the full judgment date"
MSG_DATE_INVALID = "Enter a real date"

MSG_METADATA_DATE_INCOMPLETE = "Enter the full date for the new claim"
MSG_METADATA_DATE_INVALID = "Enter a real date for the new claim"


@dataclass(frozen=True, slots=True)
class GovukDateFieldMessages:
    required: str = MSG_DATE_REQUIRED
    incomplete: str = MSG_DATE_INCOMPLETE
    invalid: str = MSG_DATE_INVALID


JUDGMENT_DATE_FIELD_MESSAGES = GovukDateFieldMessages()

METADATA_NEW_DATE_CLAIM_MESSAGES = GovukDateFieldMessages(
    required=MSG_DATE_REQUIRED,
    incomplete=MSG_METADATA_DATE_INCOMPLETE,
    invalid=MSG_METADATA_DATE_INVALID,
)


class GovukDateParseError(ValueError):
    pass


def parse_optional_govuk_date_from_post(
    data: Mapping[str, str],
    name_prefix: str,
    *,
    messages: GovukDateFieldMessages = JUDGMENT_DATE_FIELD_MESSAGES,
) -> date | None:
    day = data.get(f"{name_prefix}-day", "").strip()
    month = data.get(f"{name_prefix}-month", "").strip()
    year = data.get(f"{name_prefix}-year", "").strip()

    if not day and not month and not year:
        return None

    return parse_govuk_date_from_post(data, name_prefix, messages=messages)


def parse_govuk_date_from_post(
    data: Mapping[str, str],
    name_prefix: str,
    *,
    messages: GovukDateFieldMessages = JUDGMENT_DATE_FIELD_MESSAGES,
) -> date:
    day = data.get(f"{name_prefix}-day", "").strip()
    month = data.get(f"{name_prefix}-month", "").strip()
    year = data.get(f"{name_prefix}-year", "").strip()

    if not day and not month and not year:
        raise GovukDateParseError(messages.required)

    if not day or not month or not year:
        raise GovukDateParseError(messages.incomplete)

    try:
        return date(int(year), int(month), int(day))
    except ValueError as error:
        raise GovukDateParseError(messages.invalid) from error
