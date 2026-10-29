from datetime import UTC, datetime
from typing import Any

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import Document
from caselawclient.models.documents.metadata.fields.field import MetadataField, MetadataStringValue
from caselawclient.models.documents.metadata.fields.source import MetadataSource


def judgment_with_title_claim(
    *,
    body_name: str,
    title_claim: str,
    source: MetadataSource,
    **judgment_kwargs: Any,
) -> Document:
    judgment = JudgmentFactory.build(
        body=DocumentBodyFactory.build(name=body_name),
        **judgment_kwargs,
    )
    judgment.metadata_fields.add(
        MetadataField(
            id="title-claim",
            name="title",
            value=MetadataStringValue(title_claim),
            source=source,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    )
    return judgment
