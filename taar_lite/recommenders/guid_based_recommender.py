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


    We store the JSON data for the GUID coinstallation in memory. This
    consumes ~ 15.8MB of heap.

        In [10]: from pympler import asizeof

        In [11]: jdata = json.load(open('guid_coinstallation.json'))

        In [12]: asizeof.asizeof(jdata)
        Out[12]: 15784672

    Each of the data normalization dictionaries is also stored in
    memory.
    """
    _addons_coinstallations = None
    _guid_maps = {}

    def __init__(self, ctx):
        self._ctx = ctx
        assert IS3Data in self._ctx
        self._init_from_ctx()
        self._precompute_normalization()

    def _init_from_ctx(self):
        cache = self._ctx[IS3Data]
        self._addons_coinstallations = cache.get_s3_json_content(ADDON_LIST_BUCKET,
                                                                 ADDON_LIST_KEY)
        if self._addons_coinstallations is None:
            logger.error("Cannot download the addon coinstallation file {}".format(ADDON_LIST_KEY))

    def _precompute_normalization(self):
        if self._addons_coinstallations is None:
            logger.error("Cannot find addon coinstallations to normalize.")
            return

        # Capture the total number of times that a guid was
        # coinstalled with another GUID
        #
        # This is a map is guid->sum of coinstall counts
        guid_count_map = {}

        # Capture the number of times a GUID shows up per row
        # of coinstallation data.
        #
        # This is a map of guid->rows that this guid appears on
        row_count = {}

        guid_row_norm = {}

        for guidkey, coinstalls in self._addons_coinstallations.items():
            rowsum = sum(coinstalls.values())
            for coinstall_guid, coinstall_count in coinstalls.items():

                # Capture the total number of time a GUID was
                # coinstalled with other guids
                guid_count_map.setdefault(coinstall_guid, 0)
                guid_count_map[coinstall_guid] += coinstall_count

                # Capture the unique number of times a GUID is
                # coinstalled with other guids
                row_count.setdefault(coinstall_guid, 0)
                row_count[coinstall_guid] += 1

                if coinstall_guid not in guid_row_norm:
                    guid_row_norm[coinstall_guid] = []
                guid_row_norm[coinstall_guid].append(1.0 * coinstall_count / rowsum)

        self._guid_maps = {'count_map': guid_count_map,
                           'row_count': row_count,
                           'guid_row_norm': guid_row_norm}

    def can_recommend(self, client_data):
        # We can't recommend if we don't have our data files.
        if self._addons_coinstallations is None:
            return False

        # If we have data coming from other sources, we can use that for
        # recommending.
        addon_guid = client_data.get('guid', None)
        if not isinstance(addon_guid, str):
            return False

        # Use a dictionary keyed on the query guid
        if addon_guid not in self._addons_coinstallations.keys():
            return False

        if not self._addons_coinstallations.get(addon_guid):
            return False

        return True

    def recommend(self, client_data, limit=4):
        """
        TAAR lite will yield 4 recommendations for the AMO page
        """
        addon_guid = client_data.get('guid')
        normalize = client_data.get('normalize', None)
        norm_dict = {'row_count': self.norm_row_count,
                     'row_sum': self.norm_row_sum,
                     'rownorm_sum': self.norm_rownorm_sum}

        if normalize is not None and normalize not in norm_dict.keys():
            # Yield no results if the normalization method is not
            # specified
            logger.warn("Invalid normalization parameter detected: [%s]" % normalize)
            return []

        result_dict = self._addons_coinstallations.get(addon_guid, {})

        # Default the normalization method to no normalization
        norm_method = norm_dict.get(normalize, lambda guid, x: x)
        result_dict = norm_method(addon_guid, result_dict)

        result_list = sorted(result_dict.items(), key=lambda x: x[1], reverse=True)

        return result_list[:limit]

    def norm_row_count(self, key_guid, input_coinstall_dict):
        """This normalization method counts the unique times that a
        GUID is coinstalled with any other GUID.

        This dampens weight of any suggested GUID inversely
        proportional to it's overall popularity.
        """
        uniq_guid_map = self._guid_maps['row_count']

        output_result_dict = {}
        for result_guid, result_count in input_coinstall_dict.items():
            output_result_dict[result_guid] = 1.0 * result_count / uniq_guid_map[result_guid]
        return output_result_dict

    def norm_row_sum(self, key_guid, input_coinstall_dict):
        """This normalization normalizes the weights for the suggested
        coinstallation GUIDs based on the sum of the weights for the
        coinstallation GUIDs given a key GUID.
        """
        guid_count_map = self._guid_maps['count_map']

        def generate_row_sum_list():
            for guid, guid_weight in input_coinstall_dict.items():
                norm_guid_weight = guid_weight * 1.0 / guid_count_map[guid]
                yield guid, norm_guid_weight

        return dict(generate_row_sum_list())

    def norm_rownorm_sum(self, key_guid, input_coinstall_dict):
        """This normalization is the same as norm_row_sum, but we also
        divide the result by the sum of
        (addon coinstall instances)/(addon coinstall total instances)

        The testcase for this scenario lays out the math more
        explicitly.
        """

        # Compute an intermediary dictionary that is a row normalized
        # co-install. That is - each coinstalled guid weight is
        # divided by the sum of the weights for all coinstalled guids
        # on this row.
        tmp_dict = {}

        coinstall_total_weight = sum(input_coinstall_dict.values())
        for coinstall_guid, coinstall_weight in input_coinstall_dict.items():
            tmp_dict[coinstall_guid] = coinstall_weight / coinstall_total_weight

        guid_row_norm = self._guid_maps['guid_row_norm']

        output_dict = {}
        for output_guid, output_guid_weight in tmp_dict.items():
            output_dict[output_guid] = output_guid_weight / sum(guid_row_norm[output_guid])

        return output_dict
