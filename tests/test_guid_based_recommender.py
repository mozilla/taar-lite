import json

from moto import mock_s3
import boto3
import pytest

from srgutil.context import default_context
from taar_lite.recommenders import GuidBasedRecommender
from taar_lite.recommenders.guid_based_recommender import ADDON_LIST_BUCKET, ADDON_LIST_KEY

MOCK_DATA = {
    "guid-1": [
        ('guid-2', 1000),
        ('guid-3', 100),
        ('guid-4', 10),
        ('guid-5', 1)
        ],
    "guid-6": [
        ('guid-7', 100),
        ('guid-8', 100),
        ('guid-9', 100)
        ]
    }


@pytest.fixture
def test_ctx():
    """
    This sets up a basic context for use for testing
    """
    return default_context()


@mock_s3
def test_recommender(test_ctx):
    SAMPLE_DATA = {"key-guid": {"guid-1": 4,
                                "guid-2": 1,
                                "guid-3": 3,
                                "guid-4": 2}}

    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=ADDON_LIST_BUCKET)
    conn.Object(ADDON_LIST_BUCKET, ADDON_LIST_KEY)\
        .put(Body=json.dumps(SAMPLE_DATA))

    recommender = GuidBasedRecommender(test_ctx)
    guid = "key-guid"

    assert recommender.addons_coinstallations is not None
    results = recommender.recommend({'guid': guid})
    assert 4 == len(results)
    assert ('guid-1', 4) == results[0]

    # Last entry has weight of 1
    assert ('guid-2', 1) == results[-1]
