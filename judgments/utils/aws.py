import time

import boto3
import environ

env = environ.Env()


def invalidate_caches(uri: str) -> None:
    invalidations: list[tuple[str | None, list[str]]] = [
        (env("CLOUDFRONT_PUBLIC_DISTRIBUTION_ID", default=None), ["/*"]),
        (env("CLOUDFRONT_ASSETS_DISTRIBUTION_ID", default=None), [f"/{uri}/*"]),
        (env("CLOUDFRONT_EDITOR_DISTRIBUTION_ID", default=None), ["/*"]),
    ]
    if not any(distribution_id for distribution_id, _ in invalidations):
        return

    aws = boto3.session.Session()
    cloudfront = aws.client("cloudfront")
    for distribution_id, paths in invalidations:
        if not distribution_id:
            continue
        cloudfront.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                "Paths": {"Quantity": len(paths), "Items": paths},
                "CallerReference": str(time.time()),
            },
        )
