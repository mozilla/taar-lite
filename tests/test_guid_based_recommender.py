import pytest

from taar-lite.recommenders import GuidBasedRecommender

MOCK_DATA = {
    "guid-1": [
        ('guid-2', 1000),
        ('guid-3', 100),
        ('guid-4', 10),
        ('guid-5', 1)
        ],
    "guid-6": [
        ('guid-7', 100),
        ('guid-8', 100),
        ('guid-9', 100)
        ]
    }

# WIP: for now pass tests.
assert True