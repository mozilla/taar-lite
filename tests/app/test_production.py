from mock import patch, MagicMock

from taar_lite.app.production import (
    TaarLiteAppResource,
    LoggingMinInstallPrune,
    NORM_MODE_PROPORTIONAL_TOTAL_REL,
    NORM_MODE_DEGREE,
    NORM_MODE_TOTAL_REL,
)
from taar_lite.recommenders.treatments import (
    NoTreatment,
    DegreeNorm,
    ProportionalTotalRelevanceNorm,
    TotalRelevanceNorm,
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
    assert_recommender_match(NORM_MODE_DEGREE)
    assert_recommender_match(NORM_MODE_PROPORTIONAL_TOTAL_REL)
    assert_recommender_match(NORM_MODE_TOTAL_REL)


def test_calling_with_normalize_as_random_value_returns_empty_list(test_context):
    app_resource = TaarLiteAppResource(test_context)
    recs = app_resource.recommend({'guid': 'a', 'normalize': 'NOTARECOMMENDER'}, limit=4)
    assert recs == []


def test_recommenders_use_their_respective_treatments(test_context):
    app_resource = TaarLiteAppResource(test_context)
    recommenders = app_resource._recommenders  # noqa
    assert len(recommenders['none'].treatments) == 2
    assert isinstance(recommenders['none'].treatments[0], LoggingMinInstallPrune)
    assert isinstance(recommenders['none'].treatments[1], NoTreatment)
    assert len(recommenders[NORM_MODE_DEGREE].treatments) == 2
    assert isinstance(recommenders[NORM_MODE_DEGREE].treatments[0], LoggingMinInstallPrune)
    assert isinstance(recommenders[NORM_MODE_DEGREE].treatments[1], DegreeNorm)
    assert len(recommenders[NORM_MODE_PROPORTIONAL_TOTAL_REL].treatments) == 2
    assert isinstance(recommenders[NORM_MODE_PROPORTIONAL_TOTAL_REL].treatments[0], LoggingMinInstallPrune)
    assert isinstance(recommenders[NORM_MODE_PROPORTIONAL_TOTAL_REL].treatments[1], ProportionalTotalRelevanceNorm)
    assert len(recommenders[NORM_MODE_TOTAL_REL].treatments) == 2
    assert isinstance(recommenders[NORM_MODE_TOTAL_REL].treatments[0], LoggingMinInstallPrune)
    assert isinstance(recommenders[NORM_MODE_TOTAL_REL].treatments[1], TotalRelevanceNorm)


def test_recommenders_have_tie_breaker_dict_set(test_context):
    app_resource = TaarLiteAppResource(test_context)
    recommenders = app_resource._recommenders  # noqa
    tie_breaker_dict = app_resource._guid_rankings  # noqa
    for norm in ['none', NORM_MODE_DEGREE, NORM_MODE_PROPORTIONAL_TOTAL_REL, NORM_MODE_TOTAL_REL]:
        assert recommenders[norm].tie_breaker_dict == tie_breaker_dict
