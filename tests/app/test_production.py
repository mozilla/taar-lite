from mock import patch, MagicMock

from taar_lite.app.production import (
    TaarLiteAppResource,
    LoggingMinInstallThreshold,
    NORM_MODE_ROWCOUNT,
    NORM_MODE_ROWNORMSUM,
    NORM_MODE_ROWSUM
)
from taar_lite.recommenders.treatments import (
    NoTreatment,
    RowCount,
    RowNormSum,
    RowSum,
)


def test_calling_with_normalize_string_matches(test_context):

    def assert_recommender_match(rec_key):
        app_resource = TaarLiteAppResource(test_context)
        mock_recommender = MagicMock()
        # The important thing here is that strings dictionary_lookup and normalize_value match as expected
        with patch.dict(app_resource._recommenders, {rec_key: mock_recommender}):
            app_resource.recommend({'guid': 'a', 'normalize': rec_key}, limit=4)
        mock_recommender.recommend.assert_called_once_with('a', 4)

    assert_recommender_match('none')
    assert_recommender_match(NORM_MODE_ROWCOUNT)
    assert_recommender_match(NORM_MODE_ROWNORMSUM)
    assert_recommender_match(NORM_MODE_ROWSUM)


def test_calling_with_normalize_as_random_value_returns_empty_list(test_context):
    app_resource = TaarLiteAppResource(test_context)
    recs = app_resource.recommend({'guid': 'a', 'normalize': 'NOTARECOMMENDER'}, limit=4)
    assert recs == []


def test_recommenders_use_their_respective_treatments(test_context):
    app_resource = TaarLiteAppResource(test_context)
    recommenders = app_resource._recommenders  # noqa
    assert len(recommenders['none'].treatments) == 2
    assert isinstance(recommenders['none'].treatments[0], LoggingMinInstallThreshold)
    assert isinstance(recommenders['none'].treatments[1], NoTreatment)
    assert len(recommenders[NORM_MODE_ROWCOUNT].treatments) == 2
    assert isinstance(recommenders[NORM_MODE_ROWCOUNT].treatments[0], LoggingMinInstallThreshold)
    assert isinstance(recommenders[NORM_MODE_ROWCOUNT].treatments[1], RowCount)
    assert len(recommenders[NORM_MODE_ROWNORMSUM].treatments) == 2
    assert isinstance(recommenders[NORM_MODE_ROWNORMSUM].treatments[0], LoggingMinInstallThreshold)
    assert isinstance(recommenders[NORM_MODE_ROWNORMSUM].treatments[1], RowNormSum)
    assert len(recommenders[NORM_MODE_ROWSUM].treatments) == 2
    assert isinstance(recommenders[NORM_MODE_ROWSUM].treatments[0], LoggingMinInstallThreshold)
    assert isinstance(recommenders[NORM_MODE_ROWSUM].treatments[1], RowSum)
