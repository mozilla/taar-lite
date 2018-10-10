def normalize_row_weights(coinstall_dict):
    # Compute an intermediary dictionary that is a row normalized
    # co-install. That is - each coinstalled guid weight is
    # divided by the sum of the weights for all coinstalled guids
    # on this row.
    tmp_dict = {}
    coinstall_total_weight = sum(coinstall_dict.values())
    for coinstall_guid, coinstall_weight in coinstall_dict.items():
        tmp_dict[coinstall_guid] = coinstall_weight / coinstall_total_weight
    return tmp_dict
