# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import numpy as np
import pandas as pd

from .treatments import BaseTreatment


class GuidGuidCoinstallRecommender:
    """ A recommender class that returns top N addons based on a
    passed addon identifier.
    Accepts:
        - a dict containing coinstalled addons
        - a dict of addon rankins
        - a instance of a treatment class that transforms the original coinstallation dict

    Provides a recommend method to then return recommendations for a supplied addon.
    Can also return the complete recommendation graph.
    """

    def __init__(
            self,
            raw_coinstallation_graph,
            guid_rankings,
            treatment_cls,
            apply_treatment_on_init=True,
            validate_raw_coinstallation_graph=True):
        assert isinstance(treatment_cls, BaseTreatment)
        if validate_raw_coinstallation_graph:
            self.validate_raw_coinstallation_graph(raw_coinstallation_graph)
        self._treatment_cls = treatment_cls
        self._raw_coinstallation_graph = raw_coinstallation_graph
        self._guid_rankings = guid_rankings
        self._treatment_graph = {}
        self._min_installs = 0
        if apply_treatment_on_init:
            self.build_treatment_graph()

    @classmethod
    def validate_raw_coinstallation_graph(cls, coinstallations):
        sorted_guids = sorted(list(coinstallations.keys()))
        df = pd.DataFrame(coinstallations, index=sorted_guids, columns=sorted_guids)
        as_matrix = df.values
        assert np.allclose(as_matrix, as_matrix.T, equal_nan=True)

    @property
    def min_installs(self):
        """Returns the minimum number of installs acceptable to keep a guid in the recommendations."""
        return self._min_installs

    @property
    def raw_coinstallation_graph(self):
        """Returns a dictionary with guid keys and a coinstall set values.

        Something like this, but with much longer values.

            {
                'guid_a': {'guid_b': 10, 'guid_c': 13},
                'guid_b': {'guid_a': 10, 'guid_c': 4},
                'guid_c': {'guid_a': 13, 'guid_b': 4}
            }

        It must be symmetric.
        """
        return self._raw_coinstallation_graph

    @property
    def treatment_graph(self):
        """Returns the recommentaion graph.

        Recommendation graph is in the same format as the coinstallation graph but the
        numerical values are the weightings as a result of the treatment.
        """
        return self._recommendation_graph

    @property
    def guid_rankings(self):
        """Returns a dictionary with guid keys and install count values"""
        return self._guid_rankings

    @property
    def recommendation_graph(self, limit):
        """The recommendation graph is the full output for all addons"""
        rec_graph = {}
        for guid in self.raw_coinstallation_graph:
            rec_graph[guid] = self.recommend(guid, limit)
        return rec_graph

    def build_treatment_graph(self):
        """Does the work to compute and then set the recommendation graph.
        Sub classes may wish to override if more complex computation is required.
        """
        # TODO Is this too coupled? (Am okay leaving for now)
        self._treatment_graph = self._treatment_cls.treat(self.raw_coinstallation_graph)

    def recommend(self, for_guid, limit):
        """Returns a list of sorted recommendations of length 0 - limit for supplied guid.

        Result list is a list of tuples with the lex ranking string. e.g.
            [
                ('guid_a', '000003.000002.0001000'),
                ('guid_c', '000001.000002.0001000'),
                ('guid_b', '000001.000002.0000010'),
            ]

        """
        if for_guid not in self.treatment_graph:
            return []
        raw_recommendations = self.treatment_graph[for_guid]
        cleaned_recommendations = self._strip_low_ranked_guids(raw_recommendations)
        result_list = self._build_sorted_result_list(cleaned_recommendations)
        return result_list[:limit]

    def _strip_low_ranked_guids(self, input_dict):
        """Takes a dictionary with a format matching the values in the coinstall_dict
        and strips it of keys that do not meet the minimum installs.

            In:  {'guid_b': 10, 'guid_c': 13}
            Out: {'guid_b': 10, 'guid_c': 13}
        """

        cleaned_dict = {}
        for k, v in input_dict.items():
            if self.guid_rankings.get(k, 0) >= self.min_installs:
                cleaned_dict[k] = v
        return cleaned_dict

    def _build_sorted_result_list(self, result_dict):
        """Takes a dictionary with a format matching the values in the coinstall_dict
        and return a sorted list of results

            In: {'guid_b': 10, 'guid_c': 13}
            Out:
                [
                    ('guid_c', '000013.000000.0001000'),
                    ('guid_b', '000010.000000.0000010'),
                ]

        """
        # Augment the result_dict with the installation counts
        # and then we can sort using lexical sorting of strings.
        # The idea here is to get something in the form of
        #    0000.0000.0000
        # The computed weight takes the first and second segments of
        # integers.  The third segment is the installation count of
        # the addon but is zero padded.
        result_dict = {}
        for k, v in result_dict.items():
            lex_value = "{0:020.10f}.{1:010d}".format(v, self.guid_rankings.get(k, 0))
            result_dict[k] = lex_value
        # Sort the result dictionary in descending order by weight
        result_list = sorted(result_dict.items(), key=lambda x: x[1], reverse=True)
        return result_list
