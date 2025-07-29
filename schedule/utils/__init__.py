def extract_filter_values(filters: list, conditions: list[dict]) -> tuple:
	"""Extracts specific filter values from a filter list based on given conditions."""

	values = {next(iter(condition.keys())): None for condition in conditions}
	condition_map = {next(iter(condition.keys())): next(iter(condition.values())) for condition in conditions}

	for f in filters:
		key, operator, value = f[1], f[2], f[3]
		if key in condition_map and operator == condition_map[key]:
			values[key] = value.replace("%", "") if operator == "like" else value

	return tuple(values[key] for key in values)


def rename_keys(data: dict, rename_map: dict) -> dict:
	"""
	Rename keys in a dictionary based on a given mapping.

	:param data: The original dictionary.
	:param rename_map: A dictionary mapping old keys to new keys.
	:return: A new dictionary with renamed keys.
	"""

	return {rename_map.get(k, k): v for k, v in data.items()}
