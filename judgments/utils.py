import json
import logging
import re
import time
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
from django.contrib.auth.models import User

env = environ.Env()


VERSION_REGEX = r"(\d+)-(\d+|TDR)"


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
    new_uri = caselawutils.neutral_url(new_citation.strip())
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


def create_aws_client(service: str):  # service
    """@param: service The AWS service, e.g. 's3'"""
    aws = boto3.session.Session(
        aws_access_key_id=env("AWS_ACCESS_KEY_ID", default=None),
        aws_secret_access_key=env("AWS_SECRET_KEY", default=None),
    )
    return aws.client(
        service,
        endpoint_url=env("AWS_ENDPOINT_URL", default=None),
        region_name=env("PRIVATE_ASSET_BUCKET_REGION", default=None),
        config=botocore.client.Config(signature_version="s3v4"),
    )


def create_s3_client():
    return create_aws_client("s3")


def uri_for_s3(uri: str):
    return uri.lstrip("/")


def generate_docx_url(uri: str):
    # If there isn't a PRIVATE_ASSET_BUCKET, don't try to get the bucket.
    # This helps local environment setup where we don't use S3.
    bucket = env("PRIVATE_ASSET_BUCKET", None)
    if not bucket:
        return ""

    client = create_s3_client()

    key = f'{uri}/{uri.replace("/", "_")}.docx'

    return client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}
    )


def generate_pdf_url(uri: str):
    bucket = env("PRIVATE_ASSET_BUCKET", None)
    if not bucket:
        return ""

    client = create_s3_client()

    key = f'{uri}/{uri.replace("/", "_")}.pdf'

    return client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}
    )


def delete_from_bucket(uri: str, bucket: str) -> None:
    client = create_s3_client()
    response = client.list_objects(Bucket=bucket, Prefix=uri)

    if response.get("Contents"):
        objects_to_delete = [
            {"Key": obj["Key"]} for obj in response.get("Contents", [])
        ]
        client.delete_objects(
            Bucket=bucket,
            Delete={
                "Objects": objects_to_delete,
            },
        )


def delete_documents(uri: str) -> None:
    unpublish_documents(uri)
    delete_from_bucket(uri, env("PRIVATE_ASSET_BUCKET"))


def publish_documents(uri: str) -> None:
    client = create_s3_client()

    public_bucket = env("PUBLIC_ASSET_BUCKET")
    private_bucket = env("PRIVATE_ASSET_BUCKET")

    response = client.list_objects(Bucket=private_bucket, Prefix=uri)

    for result in response.get("Contents", []):
        key = str(result["Key"])

        if not key.endswith("parser.log") and not key.endswith(".tar.gz"):
            source = {"Bucket": private_bucket, "Key": key}
            extra_args = {"ACL": "public-read"}
            try:
                client.copy(source, public_bucket, key, extra_args)
            except botocore.client.ClientError as e:
                logging.warning(
                    f"Unable to copy file {key} to new location {public_bucket}, error: {e}"
                )


def unpublish_documents(uri: str) -> None:
    delete_from_bucket(uri, env("PUBLIC_ASSET_BUCKET"))


def notify_changed(uri: str, status: str, enrich: bool = False) -> None:
    client = create_aws_client("sns")

    message_attributes = {}
    message_attributes["update_type"] = {
        "DataType": "String",
        "StringValue": status,
    }
    message_attributes["uri_reference"] = {
        "DataType": "String",
        "StringValue": uri,
    }
    if enrich:
        message_attributes["trigger_enrichment"] = {
            "DataType": "String",
            "StringValue": "1",
        }

    client.publish(
        TopicArn=env("SNS_TOPIC"),
        Message=json.dumps({"uri_reference": uri, "status": status}),
        Subject=f"Updated: {uri} {status}",
        MessageAttributes=message_attributes,
    )


def invalidate_caches(uri: str) -> None:
    if (
        env("CLOUDFRONT_INVALIDATION_ACCESS_KEY_ID", default=None) is None
        and env("CLOUDFRONT_INVALIDATION_ACCESS_SECRET", default=None) is None
    ):
        logging.warning(
            "Cannot invalidate cache: no cloudfront environment variables set"
        )
        return

    aws = boto3.session.Session(
        aws_access_key_id=env("CLOUDFRONT_INVALIDATION_ACCESS_KEY_ID", default=None),
        aws_secret_access_key=env(
            "CLOUDFRONT_INVALIDATION_ACCESS_SECRET", default=None
        ),
    )
    cloudfront = aws.client("cloudfront")
    cloudfront.create_invalidation(
        DistributionId=env("CLOUDFRONT_PUBLIC_DISTRIBUTION_ID"),
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": str(time.time()),
        },
    )


def render_versions(decoded_versions):
    versions = [
        {
            "uri": part.text.rstrip(".xml"),
            "version": extract_version(part.text),
        }
        for part in decoded_versions
    ]
    sorted_versions = sorted(versions, key=lambda d: -d["version"])
    return sorted_versions


def extract_version(version_string: str) -> int:
    try:
        return int(re.search(VERSION_REGEX, version_string).group(1))
    except AttributeError:
        return 0


def users_dict():
    users = User.objects.all()
    return [
        {
            "name": u.get_username(),
            "print_name": u.get_full_name() or u.get_username(),
        }
        for u in users
    ]
