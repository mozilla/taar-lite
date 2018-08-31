import pytest

from taar_lite.recommenders.guidguid import GuidGuidCoinstallRecommender
from taar_lite.recommenders.treatments import NoTreatment


@pytest.fixture
def coinstall_dict():
    return {
        'a': {'b': 1, 'c': 1},
        'b': {'c': 1, 'a': 1},
        'c': {'a': 1, 'b': 1},
    }


@pytest.fixture
def ranking_dict():
    return {
        'a': 80,
        'b': 100,
        'c': 90,
    }


@pytest.fixture
def recommender(coinstall_dict, ranking_dict):
    return GuidGuidCoinstallRecommender(
        raw_coinstall_dict=coinstall_dict,
        treatments=[NoTreatment()],
        tie_breaker_dict=ranking_dict
    )


def test_sorted_result_list_breaks_ranking_tie(recommender, coinstall_dict):
    # This coinstall dict will give equal weighting to
    # everything so we want recommendations to be sorted by popularity.
    assert recommender.treated_graph == coinstall_dict
    assert recommender.recommend('a', limit=2) == [
        ('b', '000000001.0000000000.0000000100'),
        ('c', '000000001.0000000000.0000000090'),
    ]
    assert recommender.recommend('b', limit=2) == [
        ('c', '000000001.0000000000.0000000090'),
        ('a', '000000001.0000000000.0000000080'),
    ]
    assert recommender.recommend('c', limit=2) == [
        ('b', '000000001.0000000000.0000000100'),
        ('a', '000000001.0000000000.0000000080'),
    ]


def test_recommend_for_nonexistent_guid_returns_empty_list(recommender):
    assert recommender.recommend('d', 10) == []


def test_recommender_limits_the_number_of_returned_items(recommender):
    assert len(recommender.recommend('a', 1)) == 1
    assert len(recommender.recommend('a', 0)) == 0


def test_get_recommend_graph_returns_complete_rec_graph(recommender):
    assert recommender.get_recommendation_graph(limit=1) == {
        'a': [('b', '000000001.0000000000.0000000100')],
        'b': [('c', '000000001.0000000000.0000000090')],
        'c': [('b', '000000001.0000000000.0000000100')],
    }
