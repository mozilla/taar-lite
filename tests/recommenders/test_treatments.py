import pytest
from taar_lite.recommenders.treatments import (
    NoTreatment,
    DegreeNorm,
    ProportionalTotalRelevanceNorm,
    TotalRelevanceNorm,
)


@pytest.fixture
def mock_data():
    return {'guid-1': {'guid-2': 1000,
                       'guid-3': 100,
                       'guid-4': 10,
                       'guid-5': 1,
                       'guid-6': 1},
            'guid-2': {'guid-1': 50,
                       'guid-3': 40,
                       'guid-4': 20,
                       'guid-8': 30,
                       'guid-9': 10},
            'guid-3': {'guid-1': 100,
                       'guid-2': 40,
                       'guid-4': 70},
            'guid-4': {'guid-2': 20},
            "guid-6": {'guid-1': 5,
                       'guid-7': 100,
                       'guid-8': 100,
                       'guid-9': 100},
            'guid-8': {'guid-2': 30},
            'guid-9': {'guid-2': 10}}


def test_no_treatment(mock_data):
    """In no treatment case, output is input."""
    treatment = NoTreatment()
    treated_data = treatment.treat(mock_data)
    actual = treated_data['guid-1']
    expected = mock_data['guid-1']
    assert actual == expected


# TODO I have not checked that this is what we expect
# the treatment to do, I've carried over the expectations
# from the initial work, and just modified the expected data
# format to match new code setup.

def test_row_count_treatment(mock_data):
    expected_guid_2 = {
        'guid-3': 20.0,  # 50% of 40
        'guid-1': 50 / 3,  # 1/3 of 50
        'guid-8': 15.0,  # 50% of 30
        'guid-4': 20 / 3,  # 1/3 of 20
        'guid-9': 5.0,  # 50% of 10
    }
    treatment = DegreeNorm()
    treated_data = treatment.treat(mock_data)
    actual_guid_2 = treated_data['guid-2']
    assert expected_guid_2 == actual_guid_2


def test_row_norm_sum_treatment(mock_data):
    """
    Some notes on verifying:

    Numerator is the row weighted value of guid-1 : 50/150
    Denominator is the sum of the row weighted value of guid-1 in all
    other rows

    (guid-2) 50/150
    (guid-3) 100/210
    (guid-6) 5/305

    This gives us: [0.3333333333333333,
                    0.47619047619047616,
                    0.01639344262295082]

    so the final result should be (50/150) / (50/150 + 100/210 + 5/305)

    That gives a final expected weight for guid-1 to be: 0.403591682
    """
    expected_guid_2 = {
        'guid-1': (50/150) / (50/150 + 100/210 + 5/305),
        'guid-3': 0.7478143913920645,
        'guid-4': 0.2803125787748929,
        'guid-8': 0.3788819875776398,
        'guid-9': 0.1689750692520776,
    }
    treatment = ProportionalTotalRelevanceNorm()
    treated_data = treatment.treat(mock_data)
    actual_guid_2 = treated_data['guid-2']
    assert expected_guid_2 == actual_guid_2


def test_row_sum_treatment(mock_data):
    # Numerator is the value for the coinstallation
    # for the looked-up guid.
    # Denominator is the sum of all coinstallation values
    # for that guid.
    expected_guid_2 = {
        'guid-1': 50 / (5 + 50 + 100),
        'guid-3': 40 / (100 + 40),
        'guid-4': 20 / (10 + 20 + 70),
        'guid-8': 30 / (30 + 100),
        'guid-9': 10 / (10 + 100),
    }
    treatment = TotalRelevanceNorm()
    treated_data = treatment.treat(mock_data)
    actual_guid_2 = treated_data['guid-2']
    assert expected_guid_2 == actual_guid_2
