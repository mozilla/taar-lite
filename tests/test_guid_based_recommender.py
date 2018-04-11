import pytest
from srgutil.context import default_context
from taar_lite.recommenders import GuidBasedRecommender

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


def test_recommender(test_ctx):
    recommender = GuidBasedRecommender(test_ctx)
    # TODO: do important things here
    print (recommender)
