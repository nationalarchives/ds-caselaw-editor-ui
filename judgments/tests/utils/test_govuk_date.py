import pytest

from judgments.utils.govuk_date import GovukDateParseError, parse_govuk_date_from_post


def test_parse_govuk_date_from_post():
    assert (
        parse_govuk_date_from_post(
            {
                "judgment_date-day": "2",
                "judgment_date-month": "1",
                "judgment_date-year": "2023",
            },
            "judgment_date",
        ).isoformat()
        == "2023-01-02"
    )


def test_parse_govuk_date_from_post_rejects_invalid_calendar_date():
    with pytest.raises(GovukDateParseError, match="Enter a real date"):
        parse_govuk_date_from_post(
            {
                "judgment_date-day": "31",
                "judgment_date-month": "2",
                "judgment_date-year": "2023",
            },
            "judgment_date",
        )


def test_parse_govuk_date_from_post_rejects_empty_date():
    with pytest.raises(GovukDateParseError, match="Enter the judgment date"):
        parse_govuk_date_from_post(
            {
                "judgment_date-day": "",
                "judgment_date-month": "",
                "judgment_date-year": "",
            },
            "judgment_date",
        )


def test_parse_govuk_date_from_post_rejects_partial_date():
    with pytest.raises(GovukDateParseError, match="Enter the full judgment date"):
        parse_govuk_date_from_post(
            {
                "judgment_date-day": "2",
                "judgment_date-month": "",
                "judgment_date-year": "2023",
            },
            "judgment_date",
        )
