"""Untested treatments, not yet ready for production."""
from .treatments import BaseTreatment, RowNormalizationMixin


class Guidception(BaseTreatment, RowNormalizationMixin):
    """ Expected guid-2 results based on mock_data

    guid2 = {
        'guid-1': 0.2666666666666667,
        'guid-3': 0.23333333333333334,
        'guid-4': 0.16666666666666666,
        'guid-8': 0.2,
        'guid-9': 0.13333333333333333
    }

    """

    # Define recursion levels for guid-ception
    RECURSION_LEVELS = 3
    _coinstallations = {}

    def treat(self, input_dict, **kwargs):
        self._coinstallations = input_dict
        treatment_dict = {}
        for guidkey, coinstalls in input_dict.items():
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
