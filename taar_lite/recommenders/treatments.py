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
        # TODO
        guid_count_map = self._guid_maps['count_map']
        output_dict = {}
        for guid, guid_weight in input_coinstall_dict.items():
            norm_guid_weight = guid_weight * 1.0 / guid_count_map[guid]
            output_dict[guid] = norm_guid_weight
        return output_dict


class RowCount(BaseTreatment):
    """This normalization method counts the unique times that a
    GUID is coinstalled with any other GUID.

    This dampens weight of any suggested GUID inversely
    proportional to it's overall popularity.
    """

    def treat(self, input_coinstall_dict):
        # TODO
        uniq_guid_map = self._guid_maps['row_count']

        output_result_dict = {}
        for result_guid, result_count in input_coinstall_dict.items():
            output_result_dict[result_guid] = 1.0 * result_count / uniq_guid_map[result_guid]
        return output_result_dict


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

    def treat(self, input_coinstall_dict):
        tmp_dict = self._normalize_row_weights(input_coinstall_dict)
        # TODO
        guid_row_norm = self._guid_maps['guid_row_norm']

        output_dict = {}
        for output_guid, output_guid_weight in tmp_dict.items():
            guid_row_norm_list = guid_row_norm.get(output_guid, [])
            if len(guid_row_norm_list) == 0:
                self.logger.warn("Can't find GUID_ROW_NORM data for [{}]".format(output_guid))
                continue
            norm_sum = sum(guid_row_norm_list)
            if norm_sum == 0:
                self.logger.warn("Sum of GUID_ROW_NORM data for [{}] is zero.".format(output_guid))
                continue
            output_dict[output_guid] = output_guid_weight / norm_sum

        return output_dict


class Guidception(BaseTreatment, RowNormalizationMixin):

    # Define recursion levels for guid-ception
    RECURSION_LEVELS = 3

    def treat(self, input_coinstall_dict):
        tmp_dict = self._normalize_row_weights(input_coinstall_dict)
        return self._compute_recursive_results(tmp_dict, self.RECURSION_LEVELS)

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
            next_level_coinstalls = self._addons_coinstallations.get(guid, {})
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
