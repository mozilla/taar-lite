import json
import boto3
import pytest

from moto import mock_s3
from srgutil.cache import LazyJSONLoader
from srgutil.context import default_context


@pytest.fixture()
def test_context(mock_data, mock_guid_ranking):
    # Start mocking boto3
    mock_boto = mock_s3()
    mock_boto.start()

    # Setup and yield context
    bucket = "addon_list_bucket"
    addon_key = "addon_list_key"
    gr_key = "guid_ranking_key"

    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=bucket)
    conn.Object(bucket, addon_key).put(Body=json.dumps(mock_data))
    conn.Object(bucket, gr_key).put(Body=json.dumps(mock_guid_ranking))

    context = default_context()
    coinstall_loader = LazyJSONLoader(context, bucket, addon_key)
    ranking_loader = LazyJSONLoader(context, bucket, gr_key)
    context['coinstall_loader'] = coinstall_loader
    context['ranking_loader'] = ranking_loader
    yield context

    # Cleanup mocking boto3
    mock_boto.stop()


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


@pytest.fixture
def tie_mock_data():
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
                       'guid-4': 20}}


@pytest.fixture
def mock_guid_ranking():
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
def cutoff_guid_ranking():
    return {"guid-1": 10000,
            'guid-2': 9000,
            'guid-3': 8000,
            'guid-4': 7,
            'guid-5': 6000,
            "guid-6": 5000,
            'guid-7': 4000,
            'guid-8': 3000,
            'guid-9': 2000}
