import re

from judgments import converters


class TestConverters:
    def test_year_converter_parses_year(self):
        converter = converters.YearConverter()
        match = re.match(converter.regex, "1994")
        assert isinstance(match, re.Match)
        assert match.group(0) == "1994"

    def test_year_converter_converts_to_python(self):
        converter = converters.YearConverter()
        assert converter.to_python("1994") == 1994

    def test_year_converter_converts_to_url(self):
        converter = converters.YearConverter()
        assert converter.to_url(1994) == "1994"

    def test_date_converter_parses_date(self):
        converter = converters.DateConverter()
        match = re.match(converter.regex, "2022-02-28")
        assert isinstance(match, re.Match)
        assert match.group(0) == "2022-02-28"

    def test_date_converter_fails_to_parse_string(self):
        converter = converters.DateConverter()
        match = re.match(converter.regex, "202L-ab-er")
        assert match is None

    def test_court_converter_parses_court(self):
        converter = converters.CourtConverter()
        match = re.match(converter.regex, "ewhc")
        assert isinstance(match, re.Match)
        assert match.group(0) == "ewhc"

    def test_court_converter_fails_to_parse(self):
        converter = converters.CourtConverter()
        assert re.match(converter.regex, "notacourt") is None

    def test_subdivision_converter_parses_court(self):
        converter = converters.SubdivisionConverter()
        match = re.match(converter.regex, "comm")
        assert isinstance(match, re.Match)
        assert match.group(0) == "comm"

    def test_subdivision_converter_fails_to_parse(self):
        converter = converters.SubdivisionConverter()
        assert re.match(converter.regex, "notasubdivision") is None
