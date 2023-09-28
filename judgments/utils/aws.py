import logging
import time

import boto3
import botocore.client
import environ

env = environ.Env()


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
                    f"Unable to copy file {old_key} to new location {new_key}, error: {e}",
                )


def build_new_key(old_key, new_uri):
    old_filename = old_key.rsplit("/", 1)[-1]

    if old_filename.endswith((".docx", ".pdf")):
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


def generate_signed_asset_url(key: str):
    # If there isn't a PRIVATE_ASSET_BUCKET, don't try to get the bucket.
    # This helps local environment setup where we don't use S3.
    bucket = env("PRIVATE_ASSET_BUCKET", None)
    if not bucket:
        return ""

    client = create_s3_client()

    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
    )


def invalidate_caches(uri: str) -> None:
    if (
        env("CLOUDFRONT_INVALIDATION_ACCESS_KEY_ID", default=None) is None
        and env("CLOUDFRONT_INVALIDATION_ACCESS_SECRET", default=None) is None
    ):
        logging.warning(
            "Cannot invalidate cache: no cloudfront environment variables set",
        )
        return

    aws = boto3.session.Session(
        aws_access_key_id=env("CLOUDFRONT_INVALIDATION_ACCESS_KEY_ID", default=None),
        aws_secret_access_key=env(
            "CLOUDFRONT_INVALIDATION_ACCESS_SECRET",
            default=None,
        ),
    )
    cloudfront = aws.client("cloudfront")
    cloudfront.create_invalidation(
        DistributionId=env("CLOUDFRONT_PUBLIC_DISTRIBUTION_ID", default=None),
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": str(time.time()),
        },
    )
    cloudfront.create_invalidation(
        DistributionId=env("CLOUDFRONT_ASSETS_DISTRIBUTION_ID", default=None),
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": [f"/{uri}/*"]},
            "CallerReference": str(time.time()),
        },
    )
    cloudfront.create_invalidation(
        DistributionId=env("CLOUDFRONT_EDITOR_DISTRIBUTION_ID", default=None),
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": str(time.time()),
        },
    )
