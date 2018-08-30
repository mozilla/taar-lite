import json

import boto3

from moto import mock_s3
from srgutil.cache import LazyJSONLoader

from taar_lite.app.production import (
    TaarLiteAppResource,
    ADDON_LIST_BUCKET,
    ADDON_LIST_KEY,
    GUID_RANKING_KEY,
)


@mock_s3
def test_logging(default_ctx, MOCK_DATA, MOCK_GUID_RANKING):
    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=ADDON_LIST_BUCKET)
    conn.Object(ADDON_LIST_BUCKET, ADDON_LIST_KEY)\
        .put(Body=json.dumps(MOCK_DATA))
    conn.Object(ADDON_LIST_BUCKET, GUID_RANKING_KEY)\
        .put(Body=json.dumps(MOCK_GUID_RANKING))
    coinstall_loader = LazyJSONLoader(default_ctx,
                                      ADDON_LIST_BUCKET,
                                      ADDON_LIST_KEY)

    ranking_loader = LazyJSONLoader(default_ctx,
                                    ADDON_LIST_BUCKET,
                                    GUID_RANKING_KEY)

    default_ctx['coinstall_loader'] = coinstall_loader
    default_ctx['ranking_loader'] = ranking_loader

    recommender = TaarLiteAppResource(default_ctx)

    # These would error out if the object type was incorrect
    recommender.logger.error('foo')
    recommender.logger.warn('bar')
    recommender.logger.info('foo')
    recommender.logger.debug('bar')
