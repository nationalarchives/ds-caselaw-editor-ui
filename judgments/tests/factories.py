from typing import Any
from unittest.mock import Mock

from judgments.models import Judgment


class JudgmentFactory:
    # "name_of_attribute": ("name of incoming param", "default value")
    PARAMS_MAP: dict[str, tuple[str, Any]] = {
        "uri": ("uri", "test/2023/123"),
        "name": ("name", "Judgment v Judgement"),
        "neutral_citation": ("neutral_citation", "[2023] Test 123"),
        "court": ("court", "Court of Testing"),
        "judgment_date_as_string": ("judgment_date_as_string", "2023-02-03"),
        "is_published": ("is_published", False),
        "is_sensitive": ("is_sensitive", False),
        "is_anonymised": ("is_anonymised", False),
        "has_supplementary_materials": ("has_supplementary_materials", False),
        "source_name": ("source_name", "Example Uploader"),
        "source_email": ("source_email", "uploader@example.com"),
        "consignment_reference": ("consignment_reference", "TDR-12345"),
        "versions": ("versions", []),
    }

    @classmethod
    def build(cls, **kwargs) -> Judgment:
        judgment_mock = Mock(spec=Judgment, autospec=True)

        for map_to, map_from in cls.PARAMS_MAP.items():
            if map_from[0] in kwargs:
                setattr(judgment_mock.return_value, map_to, kwargs[map_from[0]])
            else:
                setattr(judgment_mock.return_value, map_to, map_from[1])

        return judgment_mock()
