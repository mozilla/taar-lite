import json

import boto3
import pytest

from srgutil.cache import LazyJSONLoader
from moto import mock_s3

from taar_lite.production import (
    GuidBasedRecommender,
    ADDON_LIST_BUCKET,
    ADDON_LIST_KEY,
    GUID_RANKING_KEY,
)

# The different kinds of results we can expect from TAARlite are
# listed below.  Note that the ordering of GUIDs returned, and even
# the set of GUIDs returned may be altered by the different weight
# normalization modes.
#
# Based on some preliminary clustering analysis, the 'rownorm_sum'
# method appears to provide qualitatively better results than the
# other normalization modes including no normalization.


# Reading the RESULTS is not entirely obvious.  The recommendation
# list consists of 2-tuples containing a guid, followed by a lexically
# sorted weight+install count.
# The weights are formatted as a fixed with zero padded float, with
# an addition suffix of a decimal and a zero padded instllation count
# for the addon.
#
# The clearest example of this is the 'rownorm_sum_tiebreak' results
# where each of the computed weights are the same (0.25), but the
# installation count varies.
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
    'rownorm_sum_tiebreak_cutoff': [('guid-1', '000000000.3333333333.0000010000'),   # noqa
                                    ('guid-3', '000000000.3333333333.0000008000'),   # noqa
                                    ('guid-5', '000000000.3333333333.0000006000')],  # noqa
    'row_sum': [('guid-1', '000000000.3225806452.0000000010'),
                ('guid-3', '000000000.2857142857.0000000008'),
                ('guid-8', '000000000.2307692308.0000000003'),
                ('guid-4', '000000000.2000000000.0000000007')],
    'guidception': [('guid-1', '000000000.2666666667.0000000010'),
                    ('guid-3', '000000000.2333333333.0000000008'),
                    ('guid-8', '000000000.2000000000.0000000003'),
                    ('guid-4', '000000000.1666666667.0000000007')]
}


def install_mock_data(MOCK_DATA, MOCK_GUID_RANKING, default_ctx):
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


@mock_s3
def test_recommender_nonormal(default_ctx, MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['default']
    install_mock_data(MOCK_DATA, MOCK_GUID_RANKING, default_ctx)

    recommender = GuidBasedRecommender(default_ctx)

    guid = "guid-1"

    actual = recommender.recommend({'guid': guid, 'normalize': 'none'}, limit=4)
    assert actual == EXPECTED_RESULTS


@mock_s3
def test_row_count_recommender(default_ctx, MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['row_count']
    install_mock_data(MOCK_DATA, MOCK_GUID_RANKING, default_ctx)

    recommender = GuidBasedRecommender(default_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'row_count'}, limit=4)

    # Note that guid-9 is not included because it's weight is
    # decreased 50% to 5
    assert EXPECTED_RESULTS == actual


@mock_s3
def test_rownorm_sumrownorm(default_ctx, MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['rownorm_sum']
    install_mock_data(MOCK_DATA, MOCK_GUID_RANKING, default_ctx)

    recommender = GuidBasedRecommender(default_ctx)
    guid = "guid-2"

    default_actual = recommender.recommend({'guid': guid}, limit=4)

    actual = recommender.recommend({'guid': guid, 'normalize': 'rownorm_sum'}, limit=4)

    # Default normalization is rownorm_sum
    assert actual == default_actual
    assert actual == EXPECTED_RESULTS
    """
    Some notes on verifying guid-1:

    Numerator is the row weighted value of guid-1 : 50/150
    Denominator is the sum of the row weighted value of guid-1 in all
    other rows

    (guid-2) 50/150
    (guid-3) 100/210
    (guid-6) 5/305

    This gives us: [0.3333333333333333,
                    0.47619047619047616,
                    0.01639344262295082]

    so the final result should be (5/150) / (50/150 + 100/210 + 5/305)

    That gives a final expected weight for guid-1 to be: 0.403591682
    """
    expected = 0.403591682
    actual = float(actual[1][1][:-11])
    assert expected == pytest.approx(actual, rel=1e-3)


@mock_s3
def test_rowsum_recommender(default_ctx, MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['row_sum']
    install_mock_data(MOCK_DATA, MOCK_GUID_RANKING, default_ctx)

    recommender = GuidBasedRecommender(default_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'row_sum'}, limit=4)
    assert 4 == len(actual)

    expected_val = 50/155
    actual_val = float(actual[0][1][:-11])
    assert expected_val == pytest.approx(actual_val, rel=1e-3)

    assert actual == EXPECTED_RESULTS


@mock_s3
def test_guidception(default_ctx, MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['guidception']
    install_mock_data(MOCK_DATA, MOCK_GUID_RANKING, default_ctx)

    recommender = GuidBasedRecommender(default_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'guidception'}, limit=4)
    assert actual == EXPECTED_RESULTS


@mock_s3
def test_rownorm_sum_tiebreak(default_ctx, TIE_MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['rownorm_sum_tiebreak']
    install_mock_data(TIE_MOCK_DATA, MOCK_GUID_RANKING, default_ctx)

    recommender = GuidBasedRecommender(default_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'rownorm_sum'}, limit=4)

    # Note that the results have weights that are equal, but the tie
    # break is solved by the install rate.
    assert actual == EXPECTED_RESULTS


@pytest.mark.skip("BIRD: I've changed this API, what do we want to test now. (suggest breaking out treatment tests)")
@mock_s3
def test_missing_rownorm_data_issue_31(default_ctx, TIE_MOCK_DATA, MOCK_GUID_RANKING):
    install_mock_data(TIE_MOCK_DATA, MOCK_GUID_RANKING, default_ctx)
    recommender = GuidBasedRecommender(default_ctx)

    EXPECTED_RESULTS = RESULTS['rownorm_sum_tiebreak']

    # Explicitly destroy the guid-4 key in the row_norm data
    del recommender._guid_maps['guid_row_norm']['guid-4']
    for i, row in enumerate(EXPECTED_RESULTS):
        if row[0] == 'guid-4':
            del EXPECTED_RESULTS[i]
            break

    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'rownorm_sum'}, limit=4)

    assert actual == EXPECTED_RESULTS


@pytest.mark.skip("BIRD: I've changed this API, what do we want to test now. (suggest breaking out treatment tests)")
@mock_s3
def test_divide_by_zero_rownorm_data_issue_31(default_ctx, TIE_MOCK_DATA, MOCK_GUID_RANKING):
    install_mock_data(TIE_MOCK_DATA, MOCK_GUID_RANKING, default_ctx)
    recommender = GuidBasedRecommender(default_ctx)

    EXPECTED_RESULTS = RESULTS['rownorm_sum_tiebreak']

    # Explicitly set the guid-4 key in the row_norm data to have a sum
    # of zero weights
    recommender._guid_maps['guid_row_norm']['guid-4'] = [0, 0, 0]

    # Destroy the guid-4 key in the expected results as a sum of 0
    # will generate a divide by zero error
    for i, row in enumerate(EXPECTED_RESULTS):
        if row[0] == 'guid-4':
            del EXPECTED_RESULTS[i]
            break

    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'rownorm_sum'}, limit=4)

    assert actual == EXPECTED_RESULTS
