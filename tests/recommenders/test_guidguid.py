from taar_lite.recommenders.guidguid import GuidGuidCoinstallRecommender
from taar_lite.recommenders.treatments import NoTreatment


def test_sorted_result_list_breaks_ranking_tie():
    # This coinstall dict will give equal weighting to
    # everything so we want recommendations to be sorted by popularity.
    coinstall_dict = {
        'a': {'b': 1, 'c': 1},
        'b': {'c': 1, 'a': 1},
        'c': {'a': 1, 'b': 1},
    }
    ranking_dict = {
        'a': 80,
        'b': 100,
        'c': 90,
    }
    recommender = GuidGuidCoinstallRecommender(
        raw_coinstall_dict=coinstall_dict,
        treatment_kwargs=dict(ranking_dict=ranking_dict),
        treatments=[NoTreatment()]
    )
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
