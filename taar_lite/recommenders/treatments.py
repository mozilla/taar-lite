class BaseTreatment:

    def treat(self, raw_coinstallation_dict):
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
    def treat(self, input_coinstall_dict):
        return input_coinstall_dict


class RowSum(BaseTreatment):
    """This normalization normalizes the weights for the suggested
    coinstallation GUIDs based on the sum of the weights for the
    coinstallation GUIDs.
    """
    def treat(self, input_coinstall_dict):
        guid_count_map = {}
        for guidkey, coinstalls in input_coinstall_dict.items():
            for coinstall_guid, coinstall_count in coinstalls.items():
                guid_count_map.setdefault(coinstall_guid, 0)
                guid_count_map[coinstall_guid] += coinstall_count

        treatment_dict = {}
        for guidkey, coinstalls in input_coinstall_dict.items():
            output_dict = {}
            for guid, guid_weight in coinstalls.items():
                norm_guid_weight = guid_weight * 1.0 / guid_count_map[guid]
                output_dict[guid] = norm_guid_weight
            treatment_dict[guidkey] = output_dict

        return treatment_dict


class RowCount(BaseTreatment):
    """This normalization method counts the unique times that a
    GUID is coinstalled with any other GUID.

    This dampens weight of any suggested GUID inversely
    proportional to it's overall popularity.
    """

    def treat(self, input_coinstall_dict):
        row_count = {}
        for guidkey, coinstalls in input_coinstall_dict.items():
            for coinstall_guid, _ in coinstalls.items():
                row_count.setdefault(coinstall_guid, 0)
                row_count[coinstall_guid] += 1

        treatment_dict = {}
        for guidkey, coinstalls in input_coinstall_dict.items():
            output_dict = {}
            for result_guid, result_count in coinstalls.items():
                output_dict[result_guid] = 1.0 * result_count / row_count[result_guid]
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

    def _build_guid_row_norm(self, input_coinstall_dict):
        guid_row_norm = {}
        for _, coinstalls in input_coinstall_dict.items():
            rowsum = sum(coinstalls.values())
            for coinstall_guid, coinstall_count in coinstalls.items():
                if coinstall_guid not in guid_row_norm:
                    guid_row_norm[coinstall_guid] = []
                guid_row_norm[coinstall_guid].append(1.0 * coinstall_count / rowsum)
        return guid_row_norm

    def treat(self, input_coinstall_dict):
        guid_row_norm = self._build_guid_row_norm(input_coinstall_dict)
        treatment_dict = {}
        for guidkey, coinstalls in input_coinstall_dict.items():
            output_dict = {}
            tmp_dict = self._normalize_row_weights(coinstalls)
            for output_guid, output_guid_weight in tmp_dict.items():
                guid_row_norm_list = guid_row_norm.get(output_guid, [])
                norm_sum = sum(guid_row_norm_list)
                output_dict[output_guid] = output_guid_weight / norm_sum
            treatment_dict[guidkey] = output_dict

        return treatment_dict


class Guidception(BaseTreatment, RowNormalizationMixin):

    # Define recursion levels for guid-ception
    RECURSION_LEVELS = 3
    _coinstallations = {}

    def treat(self, input_coinstall_dict):
        self._coinstallations = input_coinstall_dict
        treatment_dict = {}
        for guidkey, coinstalls in input_coinstall_dict.items():
            tmp_dict = self._normalize_row_weights(coinstalls)
            output_dict = self._compute_recursive_results(tmp_dict, self.RECURSION_LEVELS)
            treatment_dict[guidkey] = output_dict
        return treatment_dict

    def _recursion_penalty(self, level):
        """ Return a factor to apply to the weight for a guid recommendation."""
        dampener = 1.0 - (1.0 * (self.RECURSION_LEVELS - level) / self.RECURSION_LEVELS)
        dampener *= dampener
        return dampener

    def _compute_recursive_results(self, row_normalized_coinstall, level):
        if level <= 0:
            return row_normalized_coinstall

        # consolidated_coinstall_dict will capture values
        consolidated_coinstall_dict = {}

        # Add this level's guid weight to the consolidated result
        dampener = self._recursion_penalty(level)
        for _, _ in row_normalized_coinstall.items():
            for guid, guid_weight in row_normalized_coinstall.items():
                weight = consolidated_coinstall_dict.get(guid, 0)
                weight += (dampener*guid_weight)
                consolidated_coinstall_dict[guid] = weight

        # Add in the next level
        level -= 1
        for guid in consolidated_coinstall_dict:
            next_level_coinstalls = self._coinstallations.get(guid, {})
            if next_level_coinstalls != {}:
                # Normalize the next bunch of suggestions
                next_level_coinstalls = self._normalize_row_weights(next_level_coinstalls)

                next_level_results = self._compute_recursive_results(next_level_coinstalls, level)
                for _, next_level_weight in next_level_results.items():
                    weight = consolidated_coinstall_dict.get(guid, 0)
                    weight += next_level_weight
                    consolidated_coinstall_dict[guid] = weight

        # normalize the final results
        return self._normalize_row_weights(consolidated_coinstall_dict)
