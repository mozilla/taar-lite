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
    SAMPLE_DATA = {
            "{a0f88751-df67-4902-8da4-543cc4ce3d48}": {
                "michal@vane.pl": 1, 
                "scdl@mrvv.net": 1, 
                "jid0-OqxcSY9VMeMm8jJqJYy5KM0nmS8@jetpack": 1, 
                "jid1-BYcQOfYfmBMd9A@jetpack": 1, 
                "{abfc19d6-cde3-453a-946d-0a38aed9c90d}": 1, 
                "rested@restedclient": 1, 
                "nimbusscreencaptureff@everhelper.me": 1, 
                "s3google@translator": 1, 
                "firefox@ghostery.com": 1, 
                "2.0@disconnect.me": 1, 
                "tb-color-picker-single@codefisher.org": 1, 
                "jid1-93WyvpgvxzGATw@jetpack": 1, 
                "{2e5ff8c8-32fe-46d0-9fc8-6b8986621f3c}": 1, 
                "odoo-toggle-debug@cyrilgdn": 1, 
                "uBlock0@raymondhill.net": 2, 
                "qwantcomforfirefox@jetpack": 1, 
                "context@reverso.net": 1, 
                "{09481d87-0d89-459e-8ea0-42945a7e2df6}": 1, 
                "jid0-XWJxt5VvCXkKzQK99PhZqAn7Xbg@jetpack": 1, 
                "{b9db16a4-6edc-47ec-a1f4-b86292ed211d}": 2, 
                "{806cbba4-1bd3-4916-9ddc-e719e9ca0cbf}": 1
                }}
    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=ADDON_LIST_BUCKET)
    conn.Object(ADDON_LIST_BUCKET, ADDON_LIST_KEY)\
        .put(Body=json.dumps(SAMPLE_DATA))

    recommender = GuidBasedRecommender(test_ctx)
    guid = "{a0f88751-df67-4902-8da4-543cc4ce3d48}"

    assert recommender.addons_coinstallations is not None
    print(recommender.recommend({'guid': guid}, 10))
