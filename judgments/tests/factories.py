import datetime
from unittest.mock import Mock

import factory
from caselawclient.models.judgments import Judgment
from caselawclient.responses.search_result import SearchResult, SearchResultMetadata
from django.contrib.auth import get_user_model
from typing_extensions import (
    Any,
    TypeAlias,
)

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("email")
    email = username
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")


class JudgmentFactory:
    # "name_of_attribute": ("name of incoming param", "default value")
    PARAMS_MAP: dict[str, tuple[str, Any]] = {
        "uri": ("uri", "test/2023/123"),
        "name": ("name", "Judgment v Judgement"),
        "document_noun": ("document_noun", "judgment"),
        "neutral_citation": ("neutral_citation", "[2023] Test 123"),
        "court": ("court", "Court of Testing"),
        "document_date_as_string": ("document_date_as_string", "2023-02-03"),
        "document_date_as_date": ("document_date_as_date", datetime.date(2023, 2, 3)),
        "is_published": ("is_published", False),
        "is_failure": ("is_failure", False),
        "failed_to_parse": ("failed_to_parse", False),
        "source_name": ("source_name", "Example Uploader"),
        "source_email": ("source_email", "uploader@example.com"),
        "consignment_reference": ("consignment_reference", "TDR-12345"),
        "assigned_to": ("assigned_to", ""),
        "versions": ("versions", []),
        "versions_as_documents": ("versions_as_documents", []),
        "content_as_xml": ("xml", "<akomaNtoso>This is a document's XML.</akomaNtoso>"),
    }

    @classmethod
    def build(cls, **kwargs) -> Judgment:
        judgment_mock = Mock(spec=Judgment, autospec=True)

        if "html" in kwargs:
            judgment_mock.return_value.content_as_html.return_value = kwargs.pop("html")
        else:
            judgment_mock.return_value.content_as_html.return_value = (
                "<p>This is a judgment.</p>"
            )

        for map_to, map_from in cls.PARAMS_MAP.items():
            if map_from[0] in kwargs:
                setattr(judgment_mock.return_value, map_to, kwargs[map_from[0]])
            else:
                setattr(judgment_mock.return_value, map_to, map_from[1])

        judgment = judgment_mock()
        version = judgment.copy()
        version.version_number = 1
        version.get_latest_manifestation_datetime = datetime.datetime(2023, 9, 26, 12)
        uri = judgment.uri
        _id = uri.split("/")[-1]
        version.uri.return_value = f"{uri}/_xml_versions/1-{_id}.xml"
        judgment.versions_as_documents.append(version)

        return judgment


class SimpleFactory:
    # "name_of_attribute": ("name of incoming param", "default value")
    PARAMS_MAP: dict[str, Any]

    TargetClass: TypeAlias = object

    @classmethod
    def build(cls, **kwargs) -> TargetClass:
        mock_object = Mock(spec=cls.TargetClass, autospec=True)

        for param, default in cls.PARAMS_MAP.items():
            if param in kwargs:
                setattr(mock_object.return_value, param, kwargs[param])
            else:
                setattr(mock_object.return_value, param, default)

        return mock_object()


class SearchResultMetadataFactory(SimpleFactory):
    target_class = SearchResultMetadata
    # "name_of_attribute": ("name of incoming param", "default value")
    PARAMS_MAP = {
        "author": factory.Faker("name"),
        "author_email": factory.Faker("email"),
        "consignment_reference": "TDR-2023-ABC",
        "submission_datetime": datetime.datetime(2023, 2, 3, 9, 12, 34),
    }


class SearchResultFactory(SimpleFactory):
    target_class = SearchResult

    # "name_of_attribute": ("name of incoming param", "default value")
    PARAMS_MAP = {
        "uri": "test/2023/123",
        "name": "Judgment v Judgement",
        "neutral_citation": "[2023] Test 123",
        "court": "Court of Testing",
        "date": datetime.date(2023, 2, 3),
        "metadata": SearchResultMetadataFactory.build(),
        "is_failure": False,
        "failed_to_parse": False,
    }
