# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
from srgutil.interfaces import IS3Data

ADDON_LIST_BUCKET = 'telemetry-parquet'
ADDON_LIST_KEY = 'taar/lite/guid_coinstallation.json'

logger = logging.getLogger(__name__)


class GuidBasedRecommender:
    """ A recommender class that returns top N addons based on a passed addon identifier.
    This will load a json file containing updated top n addons coinstalled with the addon
    passed as an input parameter based on periodically updated  addon-addon coinstallation
    frequency table generated from  Longitdudinal Telemetry data.
    This recommender will drive recommendations surfaced on addons.mozilla.org
    """
    def __init__(self, ctx):
        self._ctx = ctx
        assert IS3Data in self._ctx
        self._init_from_ctx()

    def _init_from_ctx(self):
        cache = self._ctx[IS3Data]
        self.addons_coinstallations = cache.get_s3_json_content(ADDON_LIST_BUCKET,
                                                                ADDON_LIST_KEY)
        if self.addons_coinstallations is None:
            logger.error("Cannot download the addon coinstallation file {}".format(ADDON_LIST_KEY))

    def can_recommend(self, client_data):
        # We can't recommend if we don't have our data files.
        if self.addons_coinstallations is None:
            return False

        # If we have data coming from other sources, we can use that for
        # recommending.
        addon_guid = client_data.get('guid', None)
        if not isinstance(addon_guid, str):
            return False

        # Use a dictionary keyed on the query guid.    
        if addon_guid not in self.addons_coinstallations.keys():
            return False

        if not self.addons_coinstallations.get(addon_guid):
            return False

        return True

    def recommend(self, client_data, limit):
        addon_guid = client_data.get('guid')
        result_list = self.addons_coinstallations.get(addon_guid, [])[:limit]
        # TODO: normalize confidence output based on frequncy divided by total
        # frequency sum of all addon installations observed.

        # TODO: replace '1.0' with the normalized relative frequency from above
        return [(x, 1.0) for x in result_list]
