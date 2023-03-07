from typing import Any
from unittest.mock import Mock

from judgments.models import Judgment


class JudgmentFactory:
    # "name_of_attribute": ("name of incoming param", "default value")
    PARAMS_MAP: dict[str, tuple[str, Any]] = {
        "uri": ("uri", "test/2023/123"),
        "name": ("name", "Judgment v Judgement"),
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
