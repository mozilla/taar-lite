"""
Pregenerate addon recommendation results for all whitelisted addons.
"""

import json

from srgutil.context import default_context
from srgutil.interfaces import IS3Data
from taar_lite.recommenders import GuidBasedRecommender

ADDON_LIST_BUCKET = 'telemetry-parquet'
WHITELIST_KEY = 'telemetry-ml/addon_recommender/whitelist_addons_database.json'


ctx = default_context()
cache = ctx[IS3Data]

addon_whitelist = cache.get_s3_json_content(ADDON_LIST_BUCKET,
                                            WHITELIST_KEY)
grec = GuidBasedRecommender(ctx)


def compute_name(guid, addon_data):
    guid_name = addon_data['name'].get('en-US', None)
    if guid_name is None:
        guid_name = list(addon_data['name'].values())[0]
    return guid_name


output = {}
for guid in addon_whitelist.keys():
    addon_data = addon_whitelist.get(guid, None)
    addon_url = addon_data['url']
    addon_name = compute_name(guid, addon_data)

    recommendations = [x[0] for x in grec.recommend({'guid': guid}, limit=50)]

    suggestions = []
    for rec_guid in recommendations:
        rec_data = addon_whitelist[rec_guid]
        rec_name = compute_name(rec_guid, rec_data)
        rec_url = rec_data['url']
        suggestions.append({'recommendation_name': rec_name,
                            'recommendation_url': rec_url,
                            'recommendation_guid': rec_guid})

    # Strip down the suggestions to length 4 to work around the
    # coinstallation json bug
    suggestions = suggestions[:4]

    if len(suggestions) == 4:
        output[addon_url] = {'addon_name': addon_name, 'suggestions': suggestions}

json.dump(output, open('/tmp/taarlite_pregenerated.json', 'w'), indent=2)
