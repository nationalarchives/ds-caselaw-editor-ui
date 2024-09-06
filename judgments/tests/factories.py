import datetime
from typing import Any, TypeAlias
from unittest.mock import Mock

import factory
from caselawclient.client_helpers import VersionAnnotation, VersionType
from caselawclient.models.documents import Document, DocumentURIString
from caselawclient.models.judgments import Judgment
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


class DocumentFactory:
    DocumentClass: TypeAlias = Document
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
        "versions": ("versions", []),
        "versions_as_documents": ("versions_as_documents", []),
        "content_as_xml": ("xml", "<akomaNtoso>This is a document's XML.</akomaNtoso>"),
        "safe_to_delete": ("safe_to_delete", False),
    }

    @classmethod
    def build(cls, **kwargs) -> DocumentClass:
        document_mock = Mock(spec=cls.DocumentClass, autospec=True)

        original_kwargs = kwargs

        if "html" in kwargs:
            document_mock.return_value.content_as_html.return_value = kwargs.pop("html")
        else:
            document_mock.return_value.content_as_html.return_value = "<p>This is a judgment.</p>"

        for map_to, map_from in cls.PARAMS_MAP.items():
            if map_from[0] in kwargs:
                setattr(document_mock.return_value, map_to, kwargs[map_from[0]])
            else:
                setattr(document_mock.return_value, map_to, map_from[1])

        document = document_mock()

        # By default, documents should have at least one version. Create one unless either we've been explicitly
        # provided a list, or we've been told not to.
        if not document.versions_as_documents and kwargs.get("populate_versions", True):
            version = DocumentVersionFactory.build(
                populate_versions=False,
                **original_kwargs,
            )
            document.versions_as_documents.append(version)

        return document


class DocumentVersionFactory(DocumentFactory):
    DocumentClass: TypeAlias = Document

    @classmethod
    def build(cls, **kwargs) -> DocumentClass:
        kwargs["populate_versions"] = False
        document = super().build(
            **kwargs,
        )  # We don't need to strip version-specific kwargs here, because they're ditched by `DocumentFactory` anyway.

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


class JudgmentFactory(DocumentFactory):
    DocumentClass = Judgment


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
