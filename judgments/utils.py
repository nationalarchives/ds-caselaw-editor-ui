import logging
import xml.etree.ElementTree as ET
from datetime import datetime

import boto3
import botocore.client
import ds_caselaw_utils as caselawutils
import environ
from caselawclient.Client import (
    MarklogicAPIError,
    MarklogicResourceNotFoundError,
    api_client,
)

env = environ.Env()


class MoveJudgmentError(Exception):
    pass


class NeutralCitationToUriError(Exception):
    pass


def format_date(date):
    if date == "" or date is None:
        return None

    time = datetime.strptime(date, "%Y-%m-%d")
    return time.strftime("%d-%m-%Y")


def get_judgment_root(judgment_xml) -> str:
    try:
        parsed_xml = ET.XML(bytes(judgment_xml, encoding="utf-8"))
        return parsed_xml.tag
    except ET.ParseError:
        return "error"


def update_judgment_uri(old_uri, new_citation):
    new_uri = caselawutils.neutral_url(new_citation)
    if new_uri is None:
        raise NeutralCitationToUriError(
            f"Unable to form new URI for {old_uri} from neutral citation: {new_citation}"
        )

    try:
        api_client.get_judgment_xml(new_uri, show_unpublished=True)
        raise MoveJudgmentError(
            f"The URI {new_uri} generated from {new_citation} already exists, you cannot move this judgment to a"
            f" pre-existing Neutral Citation Number."
        )
    except (MarklogicAPIError, MarklogicResourceNotFoundError):
        try:
            api_client.copy_judgment(old_uri, new_uri)
            set_metadata(old_uri, new_uri)
            copy_assets(old_uri, new_uri)
            api_client.set_judgment_this_uri(new_uri)
        except MarklogicAPIError as e:
            raise MoveJudgmentError(
                f"Failure when attempting to copy judgment from {old_uri} to {new_uri}: {e}"
            )

        try:
            api_client.delete_judgment(old_uri)
        except MarklogicAPIError as e:
            raise MoveJudgmentError(
                f"Failure when attempting to delete judgment from {old_uri}: {e}"
            )

        return new_uri


def set_metadata(old_uri, new_uri):
    source_organisation = api_client.get_property(old_uri, "source-organisation")
    source_name = api_client.get_property(old_uri, "source-name")
    source_email = api_client.get_property(old_uri, "source-email")
    transfer_consignment_reference = api_client.get_property(
        old_uri, "transfer-consignment-reference"
    )
    transfer_received_at = api_client.get_property(old_uri, "transfer-received-at")
    for (key, value) in [
        ("source-organisation", source_organisation),
        ("source-name", source_name),
        ("source-email", source_email),
        ("transfer-consignment-reference", transfer_consignment_reference),
        ("transfer-received-at", transfer_received_at),
    ]:
        if value is not None:
            api_client.set_property(new_uri, key, value)

    """
    `published` is a boolean property and set differently, technically
    these failures should be unpublished but copy the property just in case.
    """
    published = api_client.get_published(old_uri)
    api_client.set_boolean_property(new_uri, "published", bool(published))


def copy_assets(old_uri, new_uri):
    client = create_s3_client()
    bucket = env("PRIVATE_ASSET_BUCKET")
    old_uri = uri_for_s3(old_uri)
    new_uri = uri_for_s3(new_uri)

    response = client.list_objects(Bucket=bucket, Prefix=old_uri)

    for result in response.get("Contents", []):
        old_key = str(result["Key"])
        new_key = build_new_key(old_key, new_uri)
        if new_key is not None:
            try:
                source = {"Bucket": bucket, "Key": old_key}
                client.copy(source, bucket, new_key)
            except botocore.client.ClientError as e:
                logging.warning(
                    f"Unable to copy file {old_key} to new location {new_key}, error: {e}"
                )


def build_new_key(old_key, new_uri):
    old_filename = old_key.rsplit("/", 1)[-1]

    if old_filename.endswith(".docx") or old_filename.endswith(".pdf"):
        new_filename = new_uri.replace("/", "_")
        return f"{new_uri}/{new_filename}.{old_filename.split('.')[-1]}"
    else:
        return f"{new_uri}/{old_filename}"


def create_s3_client():
    aws = boto3.session.Session(
        aws_access_key_id=env("AWS_ACCESS_KEY_ID", default=None),
        aws_secret_access_key=env("AWS_SECRET_KEY", default=None),
    )
    return aws.client(
        "s3",
        endpoint_url=env("AWS_ENDPOINT_URL", default=None),
        region_name=env("PRIVATE_ASSET_BUCKET_REGION", default=None),
        config=botocore.client.Config(signature_version="s3v4"),
    )


def uri_for_s3(uri: str):
    return uri.lstrip("/")
