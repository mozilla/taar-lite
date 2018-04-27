import json

from moto import mock_s3
import boto3
import pytest

from taar_lite.recommenders import GuidBasedRecommender
from taar_lite.recommenders.guid_based_recommender import ADDON_LIST_BUCKET, ADDON_LIST_KEY

# The different kinds of results we can expect from TAARlite are
# listed below.  Note that the ordering of GUIDs returned, and even
# the set of GUIDs returned may be altered by the different weight
# normalization modes.
#
# Based on some preliminary clustering analysis, the 'rownorm_sum'
# method appears to provide qualitatively better results than the
# other normalization modes including no normalization.

RESULTS = {
    'default': [('guid-2', 1000),
                ('guid-3', 100),
                ('guid-4', 10),
                ('guid-5', 1)],
    'row_count': [('guid-3', 20.0),  # 50% of 40
                  ('guid-1', 16.666666666666668),  # 1/3 of 50
                  ('guid-8', 15.0),  # 50% of 30
                  ('guid-4', 6.666666666666667)],  # 1/3 of 20
    'rownorm_sum': [('guid-3', 0.7478143913920645),
                    ('guid-1', 0.4035916824196597),
                    ('guid-8', 0.3788819875776398),
                    ('guid-4', 0.2803125787748929)],
    'row_sum': [('guid-1', 0.3225806451612903),
                ('guid-3', 0.2857142857142857), ('guid-8', 0.23076923076923078),
                ('guid-4', 0.2)],
    'guidception': [('guid-1', 0.2666666666666667),
                    ('guid-3', 0.23333333333333334),
                    ('guid-8', 0.2),
                    ('guid-4', 0.16666666666666666)]
}


def install_mock_data(MOCK_DATA):
    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=ADDON_LIST_BUCKET)
    conn.Object(ADDON_LIST_BUCKET, ADDON_LIST_KEY)\
        .put(Body=json.dumps(MOCK_DATA))


def compare_actual_expected(inputs):
    """
    Compare two 2-tuples where the first element is a guid, and the
    second is a float.

    ex: compare_actual_expected(('guid-1': 0.111111111), ('guid-1', 0.111))
    will yield True
    """
    (actual_tuple, expected_tuple) = inputs
    assert len(actual_tuple) == len(expected_tuple) == 2
    assert actual_tuple[1] == pytest.approx(expected_tuple[1], rel=1e-3)
    return True


@mock_s3
def test_recommender_nonormal(test_ctx, MOCK_DATA):
    EXPECTED_RESULTS = RESULTS['default']
    install_mock_data(MOCK_DATA)

    recommender = GuidBasedRecommender(test_ctx)
    guid = "guid-1"

    actual = recommender.recommend({'guid': guid})
    assert actual == EXPECTED_RESULTS


@mock_s3
def test_row_count_recommender(test_ctx, MOCK_DATA):
    EXPECTED_RESULTS = RESULTS['row_count']
    install_mock_data(MOCK_DATA)

    recommender = GuidBasedRecommender(test_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'row_count'})

    # Note that guid-9 is not included because it's weight is
    # decreased 50% to 5
    assert EXPECTED_RESULTS == actual


@mock_s3
def test_rownorm_sumrownorm(test_ctx, MOCK_DATA):
    EXPECTED_RESULTS = RESULTS['rownorm_sum']
    install_mock_data(MOCK_DATA)

    recommender = GuidBasedRecommender(test_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'rownorm_sum'})
    assert actual == EXPECTED_RESULTS
    """
    Some notes on verifying guid-1:

    Numerator is the row weighted value of guid-1 : 50/150
    Denominator is the sum of the row weighted value of guid-1 in all other rows

    (guid-2) 50/150
    (guid-3) 100/210
    (guid-6) 5/305

    This gives us: [0.3333333333333333, 0.47619047619047616, 0.01639344262295082]

    so the final result should be (5/150) / (50/150 + 100/210 + 5/305)

    That gives a final expected weight for guid-1 to be: 0.403591682
    """
    expected = ('guid-1', 0.403591682)
    assert compare_actual_expected((actual[1], expected))


@mock_s3
def test_rowsum_recommender(test_ctx, MOCK_DATA):
    EXPECTED_RESULTS = RESULTS['row_sum']
    install_mock_data(MOCK_DATA)

    recommender = GuidBasedRecommender(test_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'row_sum'})
    assert 4 == len(actual)
    assert compare_actual_expected((('guid-1', 50/155), actual[0]))
    assert actual == EXPECTED_RESULTS


@mock_s3
def test_guidception(test_ctx, MOCK_DATA):
    EXPECTED_RESULTS = RESULTS['guidception']
    install_mock_data(MOCK_DATA)

    recommender = GuidBasedRecommender(test_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'guidception'})
    assert actual == EXPECTED_RESULTS
