from moto import mock_s3
from taar_lite.recommenders import GuidBasedRecommender  # noqa
from taar_lite.recommenders.cache import LazyJSONLoader  # noqa
from taar_lite.recommenders.guid_based_recommender import ADDON_LIST_BUCKET
from taar_lite.recommenders.guid_based_recommender import ADDON_LIST_KEY
from taar_lite.recommenders.guid_based_recommender import GUID_RANKING_KEY
import boto3
import json
from .conftest import mock_cold_redis_cache
from unittest.mock import Mock


def install_mock_data(MOCK_DATA, MOCK_GUID_RANKING):
    conn = boto3.resource('s3', region_name='us-west-2')

    conn.create_bucket(Bucket=ADDON_LIST_BUCKET)

    conn.Object(ADDON_LIST_BUCKET, ADDON_LIST_KEY)\
        .put(Body=json.dumps(MOCK_DATA))
    conn.Object(ADDON_LIST_BUCKET, GUID_RANKING_KEY)\
        .put(Body=json.dumps(MOCK_GUID_RANKING))


def test_get_json_hot_cache(default_ctx):
    coinstall_loader = LazyJSONLoader(default_ctx,
                                      ADDON_LIST_BUCKET,
                                      ADDON_LIST_KEY)

    coinstall_loader._redis = Mock()

    # Set the redis cache as hot
    coinstall_loader._redis.exists.return_value = True
    # Set the locally cached JSON data object
    coinstall_loader._cached_copy = {"payload": "hot cached copy"}

    actual = coinstall_loader.get()
    assert actual == {"payload": "hot cached copy"}


@mock_s3
def test_get_json_cold_cache(default_ctx, MOCK_DATA, MOCK_GUID_RANKING):
    install_mock_data(MOCK_DATA, MOCK_GUID_RANKING)
    coinstall_loader = LazyJSONLoader(default_ctx,
                                      ADDON_LIST_BUCKET,
                                      ADDON_LIST_KEY)

    mock_cold_redis_cache(coinstall_loader)

    actual = coinstall_loader.get()

    # The data from the S3 mocking should be loaded here
    assert actual == MOCK_DATA
