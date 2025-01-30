import time

import boto3
import environ

env = environ.Env()


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
