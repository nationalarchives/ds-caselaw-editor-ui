import datetime


class YearConverter:
    regex = "[0-9]{4}"

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return f"{value:4d}"


class DateConverter:
    regex = "([0-9]{4})-([0-9]{2})-([0-9]{2})"

    def to_python(self, value):
        return datetime.datetime.strptime(value, "%Y-%m-%d")

    def to_url(self, value):
        if value is None:
            raise ValueError

        return value.strftime("%Y-%m-%d")


class CourtConverter:
    regex = "ewhc|uksc|ukpc|ewca|ewcop|ewfc|ukut|eat|ukftt|ukait|ukiptrib|ewcc|ewcr"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


class SubdivisionConverter:
    regex = "civ|crim|admin|admlty|ch|comm|costs|fam|ipec|mercantile|pat|qb|kb|iac|lc|tcc|aac|scco|tc|grc|b|t1|t2|t3"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value
