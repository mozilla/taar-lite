from taar_lite.recommenders.treatments import (
    NoTreatment,
    RowCount,
    RowNormSum,
    RowSum,
)

# TODO I think just invoking mock_data makes it harder
# to see whether these tests are testing the right thing.
# Propose putting data in tests.


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
    treatment = RowCount()
    treated_data = treatment.treat(mock_data)
    actual_guid_2 = treated_data['guid-2']
    assert expected_guid_2 == actual_guid_2
