import json
import boto3
import pytest

from moto import mock_s3
from srgutil.cache import LazyJSONLoader
from srgutil.context import default_context


@pytest.fixture()
def test_context():
    # Start mocking boto3
    mock_boto = mock_s3()
    mock_boto.start()

    # Setup and yield context
    bucket = "addon_list_bucket"
    addon_key = "addon_list_key"
    gr_key = "guid_ranking_key"

    coinstall_dict = {'a': {'b': 1}, 'b': {'a': 1}}
    ranking_dict = {'a': 1, 'b': 1}

    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=bucket)
    conn.Object(bucket, addon_key).put(Body=json.dumps(coinstall_dict))
    conn.Object(bucket, gr_key).put(Body=json.dumps(ranking_dict))

    context = default_context()
    coinstall_loader = LazyJSONLoader(context, bucket, addon_key)
    ranking_loader = LazyJSONLoader(context, bucket, gr_key)
    context['coinstall_loader'] = coinstall_loader
    context['ranking_loader'] = ranking_loader
    yield context

    # Cleanup mocking boto3
    mock_boto.stop()
