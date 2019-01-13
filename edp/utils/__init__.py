def is_dict_subset(source: dict, subset: dict) -> bool:
    for key, value in subset.items():
        if key not in source:
            return False
        if source[key] != subset[key]:
            return False

    return True
