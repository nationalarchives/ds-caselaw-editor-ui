import time

import boto3
import botocore.client
import environ

env = environ.Env()


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
    aws = boto3.session.Session()
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
