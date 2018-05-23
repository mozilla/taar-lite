"""
These are global fixtures automagically loaded by pytest
"""

import pytest
from srgutil.context import default_context
from unittest.mock import Mock
from threading import Lock


@pytest.fixture
def MOCK_DATA():
    return {"guid-1": {'guid-2': 1000,
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
            'guid-9': {'guid-2': 10},
            }


@pytest.fixture
def TIE_MOCK_DATA():
    return {"guid-1": {'guid-2': 100,
                       'guid-3': 100,
                       'guid-4': 100,
                       'guid-5': 100},
            'guid-2': {'guid-1': 100,
                       'guid-3': 100,
                       'guid-4': 100,
                       'guid-5': 100},
            'guid-3': {'guid-1': 100,
                       'guid-2': 100,
                       'guid-4': 100,
                       'guid-5': 100},
            'guid-4': {'guid-1': 20,
                       'guid-2': 20,
                       'guid-3': 20,
                       'guid-5': 20},
            'guid-5': {'guid-1': 20,
                       'guid-2': 20,
                       'guid-3': 20,
                       'guid-4': 20},
            }


@pytest.fixture
def MOCK_GUID_RANKING():
    return {"guid-1": 10,
            'guid-2': 9,
            'guid-3': 8,
            'guid-4': 7,
            'guid-5': 6,
            "guid-6": 5,
            'guid-7': 4,
            'guid-8': 3,
            'guid-9': 2}


@pytest.fixture
def CUTOFF_GUID_RANKING():
    return {"guid-1": 10000,
            'guid-2': 9000,
            'guid-3': 8000,
            'guid-4': 7,
            'guid-5': 6000,
            "guid-6": 5000,
            'guid-7': 4000,
            'guid-8': 3000,
            'guid-9': 2000}


@pytest.fixture
def default_ctx():
    """
    This sets up a basic context for use for testing
    """
    ctx = default_context()
    ctx['ignore_redis'] = True
    ctx['CACHE_URL'] = "redis://redis:6369/0"
    return ctx


def mock_cold_redis_cache(json_loader):
    """
    Mock out the methods of the jsonloader and return it
    """
    json_loader._redis = Mock()

    # Set the redis cache as cold
    json_loader._redis.exists.return_value = False

    # Set the redis cache as cold
    json_loader._redis.get.return_value = None

    json_loader._redis.lock.return_value = Lock()

    # Set the locally cached JSON data object to None
    json_loader._cached_copy = None

    return json_loader
