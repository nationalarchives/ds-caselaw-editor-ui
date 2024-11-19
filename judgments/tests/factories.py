import datetime
from typing import Any, TypeAlias
from unittest.mock import Mock

import factory
from caselawclient.client_helpers import VersionAnnotation, VersionType
from caselawclient.factories import DocumentFactory
from caselawclient.models.documents import Document, DocumentURIString
from caselawclient.responses.search_result import SearchResult, SearchResultMetadata
from django.contrib.auth import get_user_model
from factory.faker import faker

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("email")
    email = username
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")


class DocumentVersionFactory(DocumentFactory):
    DocumentClass: TypeAlias = Document

    @classmethod
    def build(
        cls,
        uri="test/2023/123",
        html="<p>This is a Document Version.</p>",
        api_client=None,
        **kwargs: Any,
    ) -> DocumentClass:
        kwargs["populate_versions"] = False
        document = super().build(
            **kwargs,
        )

        # Note: this function was created for the Editor version of DocumentFactory, and
        # moved to the API Client version. It's entirely possible that some parts don't make
        # coherent sense.

        version = document

        annotation: VersionAnnotation | str = kwargs.get(
            "annotation",
            VersionAnnotation(VersionType.SUBMISSION, automated=True),
        )
        if isinstance(annotation, VersionAnnotation):
            annotation.set_calling_function("factory build")
            annotation.set_calling_agent("EUI Test")
            version.annotation = annotation.as_json
        else:
            version.annotation = annotation

        version.version_number = kwargs.get("version_number", 1)
        version.version_created_datetime = kwargs.get(
            "version_created_datetime",
            datetime.datetime(2023, 9, 26, 12),
        )

        uri = document.uri
        _id = uri.split("/")[-1]
        version.uri = DocumentURIString(
            f"{uri}/_xml_versions/{version.version_number}-{_id}.xml",
        )

        return version


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
    fake = faker.Faker()
    target_class = SearchResultMetadata
    # "name_of_attribute": ("name of incoming param", "default value")
    PARAMS_MAP = {
        "author": fake.name(),
        "author_email": fake.email(),
        "consignment_reference": "TDR-2023-ABC",
        "submission_datetime": datetime.datetime(2023, 2, 3, 9, 12, 34),
        "editor_status": "published",
    }


class SearchResultFactory(SimpleFactory):
    fake = faker.Faker()
    target_class = SearchResult

    # "name_of_attribute": ("name of incoming param", "default value")
    PARAMS_MAP = {
        "uri": "test/2023/123",
        "name": f"{fake.name()} v {fake.name()}",
        "neutral_citation": "[2023] Test 123",
        "court": {"name": "Court of Testing"},
        "date": datetime.date(2023, 2, 3),
        "document_date_as_date": datetime.date(2023, 2, 3),
        "metadata": SearchResultMetadataFactory.build(),
        "is_failure": False,
        "failed_to_parse": False,
        "status": "NEW",
        "consignment_reference": "TDR-2023-ABC",
        "document_noun": "Judgment",
        "best_human_identifier": "[2023] Test 123",
        "court_and_jurisdiction_identifier_string": "Court of Testing",
    }
