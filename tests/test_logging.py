from moto import mock_s3
from taar_lite.recommenders import GuidBasedRecommender
from taar_lite.recommenders.guid_based_recommender import ADDON_LIST_BUCKET
from taar_lite.recommenders.guid_based_recommender import ADDON_LIST_KEY
from taar_lite.recommenders.guid_based_recommender import GUID_RANKING_KEY
import boto3
import json
from taar_lite.recommenders.cache import LazyJSONLoader


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

    recommender = GuidBasedRecommender(default_ctx)

    # These would error out if the object type was incorrect
    recommender.logger.error('foo')
    recommender.logger.warn('bar')
    recommender.logger.info('foo')
    recommender.logger.debug('bar')
