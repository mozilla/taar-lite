import json

from moto import mock_s3
import boto3
import pytest

from taar_lite.recommenders import GuidBasedRecommender
from taar_lite.recommenders.guid_based_recommender import ADDON_LIST_BUCKET
from taar_lite.recommenders.guid_based_recommender import ADDON_LIST_KEY
from taar_lite.recommenders.guid_based_recommender import GUID_RANKING_KEY

# The different kinds of results we can expect from TAARlite are
# listed below.  Note that the ordering of GUIDs returned, and even
# the set of GUIDs returned may be altered by the different weight
# normalization modes.
#
# Based on some preliminary clustering analysis, the 'rownorm_sum'
# method appears to provide qualitatively better results than the
# other normalization modes including no normalization.

RESULTS = {
    'default': [('guid-2', '000001000.0000000000.0000000009'),
                ('guid-3', '000000100.0000000000.0000000008'),
                ('guid-4', '000000010.0000000000.0000000007'),
                ('guid-5', '000000001.0000000000.0000000006')],
    'row_count': [('guid-3', '000000020.0000000000.0000000008'),   # 50% of 40
                  ('guid-1', '000000016.6666666667.0000000010'),  # 1/3 of 50
                  ('guid-8', '000000015.0000000000.0000000003'),  # 50% of 30
                  ('guid-4', '000000006.6666666667.0000000007')],  # 1/3 of 20
    'rownorm_sum': [('guid-3', '000000000.7478143914.0000000008'),
                    ('guid-1', '000000000.4035916824.0000000010'),
                    ('guid-8', '000000000.3788819876.0000000003'),
                    ('guid-4', '000000000.2803125788.0000000007')],
    'rownorm_sum_tiebreak': [('guid-1', '000000000.2500000000.0000000010'),
                             ('guid-3', '000000000.2500000000.0000000008'),
                             ('guid-4', '000000000.2500000000.0000000007'),
                             ('guid-5', '000000000.2500000000.0000000006')],
    'row_sum': [('guid-1', '000000000.3225806452.0000000010'),
                ('guid-3', '000000000.2857142857.0000000008'),
                ('guid-8', '000000000.2307692308.0000000003'),
                ('guid-4', '000000000.2000000000.0000000007')],
    'guidception': [('guid-1', '000000000.2666666667.0000000010'),
                    ('guid-3', '000000000.2333333333.0000000008'),
                    ('guid-8', '000000000.2000000000.0000000003'),
                    ('guid-4', '000000000.1666666667.0000000007')]
}


def install_mock_data(MOCK_DATA, MOCK_GUID_RANKING):

    conn = boto3.resource('s3', region_name='us-west-2')

    conn.create_bucket(Bucket=ADDON_LIST_BUCKET)

    conn.Object(ADDON_LIST_BUCKET, ADDON_LIST_KEY)\
        .put(Body=json.dumps(MOCK_DATA))
    conn.Object(ADDON_LIST_BUCKET, GUID_RANKING_KEY)\
        .put(Body=json.dumps(MOCK_GUID_RANKING))


@mock_s3
def test_recommender_nonormal(default_ctx, MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['default']
    install_mock_data(MOCK_DATA, MOCK_GUID_RANKING)

    recommender = GuidBasedRecommender(default_ctx)
    guid = "guid-1"

    actual = recommender.recommend({'guid': guid, 'normalize': 'none'})
    assert actual == EXPECTED_RESULTS


@mock_s3
def test_row_count_recommender(default_ctx, MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['row_count']
    install_mock_data(MOCK_DATA, MOCK_GUID_RANKING)

    recommender = GuidBasedRecommender(default_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'row_count'})

    # Note that guid-9 is not included because it's weight is
    # decreased 50% to 5
    assert EXPECTED_RESULTS == actual


@mock_s3
def test_rownorm_sumrownorm(default_ctx, MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['rownorm_sum']
    install_mock_data(MOCK_DATA, MOCK_GUID_RANKING)

    recommender = GuidBasedRecommender(default_ctx)
    guid = "guid-2"

    default_actual = recommender.recommend({'guid': guid})

    actual = recommender.recommend({'guid': guid, 'normalize': 'rownorm_sum'})

    # Default normalization is rownorm_sum
    assert actual == default_actual
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
    expected = 0.403591682
    actual = float(actual[1][1][:-11])
    assert expected == pytest.approx(actual, rel=1e-3)


@mock_s3
def test_rowsum_recommender(default_ctx, MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['row_sum']
    install_mock_data(MOCK_DATA, MOCK_GUID_RANKING)

    recommender = GuidBasedRecommender(default_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'row_sum'})
    assert 4 == len(actual)

    expected_val = 50/155
    actual_val = float(actual[0][1][:-11])
    assert expected_val == pytest.approx(actual_val, rel=1e-3)

    assert actual == EXPECTED_RESULTS


@mock_s3
def test_guidception(default_ctx, MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['guidception']
    install_mock_data(MOCK_DATA, MOCK_GUID_RANKING)

    recommender = GuidBasedRecommender(default_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'guidception'})
    assert actual == EXPECTED_RESULTS


@mock_s3
def test_rownorm_sum_tiebreak(default_ctx, TIE_MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['rownorm_sum_tiebreak']
    install_mock_data(TIE_MOCK_DATA, MOCK_GUID_RANKING)

    recommender = GuidBasedRecommender(default_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'rownorm_sum'})

    # Note that the results have weights that are equal, but the tie
    # break is solved by the install rate
    assert actual == EXPECTED_RESULTS
