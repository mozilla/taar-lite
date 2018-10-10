"""All treatments in here are heavily coupled with the
GuidGuidCoinstallRecommender.

Note (Bird Sep '18): In future may want to think about how to structure this
so the coupling is clear. I think the structure roughly makes sense, but the
implementation could be tidier / less error prone.
"""
import numpy as np


class BaseTreatment:

    def treat(self, input_dict, **kwargs):
        """Accept a coinstallation graph, and returns a treated graph.
        No constraints are put on the shape of the return graph but the format
        is expected to be the same.

        Graph format:

            {
                'guid_a': {'guid_b': 10, 'guid_c': 13},
                'guid_b': {'guid_a': 10, 'guid_c': 4},
                'guid_c': {'guid_a': 13, 'guid_b': 4}
            }

        """
        raise NotImplementedError


class NoTreatment(BaseTreatment):
    """Returns the original coinstallation dict"""
    def treat(self, input_dict, *args, **kwargs):
        return input_dict


class MinInstallPrune(BaseTreatment):
    """Takes a coinstall dictionary with a format matching the
    values in the coinstall_dict. And a ranking dictionary that
    has keys of guids and values of rank.

    It returns a coinstall dictionary stripped of keys
    that do not meet the minimum installs.

        In:  {'guid_b': 10, 'guid_c': 13}
        Out: {'guid_b': 10, 'guid_c': 13}
    """
    min_installs = 0

    def _set_min_install_threshold(self, ranking_dict):
        # Compute the floor install incidence that recommended addons
        # must satisfy.  Take 5% of the mean of all installed addons.
        self.min_installs = np.mean(list(ranking_dict.values())) * 0.05

    def treat(self, input_dict, **kwargs):
        ranking_dict = kwargs['ranking_dict']
        self._set_min_install_threshold(ranking_dict)
        cleaned_dict = {}
        for k, v in input_dict.items():
            if ranking_dict.get(k, 0) >= self.min_installs:
                cleaned_dict[k] = v
        return cleaned_dict


class DegreeNorm(BaseTreatment):
    """This normalization method counts the unique times that a
    GUID is coinstalled with any other GUID.

    This dampens weight of any suggested GUID inversely
    proportional to it's overall popularity.
    """

    def treat(self, input_dict, **kwargs):
        row_count = {}
        for guidkey, coinstalls in input_dict.items():
            for coinstall_guid, _ in coinstalls.items():
                row_count.setdefault(coinstall_guid, 0)
                row_count[coinstall_guid] += 1

        treatment_dict = {}
        for guidkey, coinstalls in input_dict.items():
            output_dict = {}
            for result_guid, result_count in coinstalls.items():
                output_dict[result_guid] = 1.0 * result_count / row_count[result_guid]
            treatment_dict[guidkey] = output_dict

        return treatment_dict


class TotalRelevanceNorm(BaseTreatment):
    """This normalization normalizes the weights for the suggested
    coinstallation GUIDs based on the sum of the weights for the
    coinstallation GUIDs.
    """
    def treat(self, input_dict, **kwargs):
        guid_count_map = {}
        for guidkey, coinstalls in input_dict.items():
            for coinstall_guid, coinstall_count in coinstalls.items():
                guid_count_map.setdefault(coinstall_guid, 0)
                guid_count_map[coinstall_guid] += coinstall_count

        treatment_dict = {}
        for guidkey, coinstalls in input_dict.items():
            output_dict = {}
            for guid, guid_weight in coinstalls.items():
                norm_guid_weight = guid_weight * 1.0 / guid_count_map[guid]
                output_dict[guid] = norm_guid_weight
            treatment_dict[guidkey] = output_dict

        return treatment_dict


class RowNormalizationMixin():

    def _normalize_row_weights(self, coinstall_dict):
        # Compute an intermediary dictionary that is a row normalized
        # co-install. That is - each coinstalled guid weight is
        # divided by the sum of the weights for all coinstalled guids
        # on this row.
        tmp_dict = {}
        coinstall_total_weight = sum(coinstall_dict.values())
        for coinstall_guid, coinstall_weight in coinstall_dict.items():
            tmp_dict[coinstall_guid] = coinstall_weight / coinstall_total_weight
        return tmp_dict


class RowNormSum(BaseTreatment, RowNormalizationMixin):
    """This normalization is the same as norm_row_sum, but we also
    divide the result by the sum of
    (addon coinstall instances)/(addon coinstall total instances)

    The testcase for this scenario lays out the math more
    explicitly.
    """

    def _build_guid_row_norm(self, input_dict):
        guid_row_norm = {}
        for _, coinstalls in input_dict.items():
            rowsum = sum(coinstalls.values())
            for coinstall_guid, coinstall_count in coinstalls.items():
                if coinstall_guid not in guid_row_norm:
                    guid_row_norm[coinstall_guid] = []
                guid_row_norm[coinstall_guid].append(1.0 * coinstall_count / rowsum)
        return guid_row_norm

    def treat(self, input_dict, **kwargs):
        guid_row_norm = self._build_guid_row_norm(input_dict)
        treatment_dict = {}
        for guidkey, coinstalls in input_dict.items():
            output_dict = {}
            tmp_dict = self._normalize_row_weights(coinstalls)
            for output_guid, output_guid_weight in tmp_dict.items():
                guid_row_norm_list = guid_row_norm.get(output_guid, [])
                norm_sum = sum(guid_row_norm_list)
                output_dict[output_guid] = output_guid_weight / norm_sum
            treatment_dict[guidkey] = output_dict

        return treatment_dict
