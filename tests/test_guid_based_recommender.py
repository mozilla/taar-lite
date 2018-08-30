import json

import boto3
import pytest

from srgutil.cache import LazyJSONLoader
from moto import mock_s3

from taar_lite.app.production import (
    TaarLiteAppResource,
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

@pytest.mark.skip("BIRD: Guidception no longer included in production. Will add tests elsewhere")
@mock_s3
def test_guidception(default_ctx, MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['guidception']
    install_mock_data(MOCK_DATA, MOCK_GUID_RANKING, default_ctx)

    recommender = TaarLiteAppResource(default_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'guidception'}, limit=4)
    assert actual == EXPECTED_RESULTS


@mock_s3
def test_rownorm_sum_tiebreak(default_ctx, TIE_MOCK_DATA, MOCK_GUID_RANKING):
    EXPECTED_RESULTS = RESULTS['rownorm_sum_tiebreak']
    install_mock_data(TIE_MOCK_DATA, MOCK_GUID_RANKING, default_ctx)

    recommender = TaarLiteAppResource(default_ctx)
    guid = "guid-2"

    actual = recommender.recommend({'guid': guid, 'normalize': 'rownorm_sum'}, limit=4)

    # Note that the results have weights that are equal, but the tie
    # break is solved by the install rate.
    assert actual == EXPECTED_RESULTS
