import time
from collections.abc import Sequence

import boto3
import environ

env = environ.Env()

MAX_PATHS_PER_INVALIDATION = 3000


def invalidate_caches(uri: str) -> None:
    invalidate_caches_for_uris([uri])


def invalidate_caches_for_uris(uris: Sequence[str]) -> None:
    """Invalidate CloudFront for several documents with one request per distribution.

    The public and editor distributions are invalidated wholesale, so that happens once
    however many documents changed. Asset paths are per document and are sent in batches.
    """
    if not uris:
        return

    invalidations: list[tuple[str | None, list[str]]] = [
        (env("CLOUDFRONT_PUBLIC_DISTRIBUTION_ID", default=None), ["/*"]),
        (env("CLOUDFRONT_ASSETS_DISTRIBUTION_ID", default=None), [f"/{uri}/*" for uri in uris]),
        (env("CLOUDFRONT_EDITOR_DISTRIBUTION_ID", default=None), ["/*"]),
    ]
    if not any(distribution_id for distribution_id, _ in invalidations):
        return

    aws = boto3.session.Session()
    cloudfront = aws.client("cloudfront")
    for distribution_id, paths in invalidations:
        if not distribution_id:
            continue
        for start in range(0, len(paths), MAX_PATHS_PER_INVALIDATION):
            batch = paths[start : start + MAX_PATHS_PER_INVALIDATION]
            cloudfront.create_invalidation(
                DistributionId=distribution_id,
                InvalidationBatch={
                    "Paths": {"Quantity": len(batch), "Items": batch},
                    "CallerReference": str(time.time()),
                },
            )
