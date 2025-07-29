from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from frappe.utils import get_datetime, get_system_timezone


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


def convert_to_utc(
	date_time: datetime | str, from_timezone: str | None = None, naive: bool = False
) -> "datetime":
	"""Converts the given datetime to UTC timezone."""

	dt = get_datetime(date_time)
	if dt.tzinfo is None:
		tz = ZoneInfo(from_timezone or get_system_timezone())
		dt = dt.replace(tzinfo=tz)

	utc_dt = dt.astimezone(timezone.utc)
	return utc_dt.replace(tzinfo=None) if naive else utc_dt


def add_or_update_tzinfo(date_time: datetime | str, timezone: str | None = None) -> str:
	"""Adds or updates timezone to the datetime."""

	date_time = get_datetime(date_time)
	target_tz = ZoneInfo(timezone or get_system_timezone())

	if date_time.tzinfo is None:
		date_time = date_time.replace(tzinfo=target_tz)
	else:
		date_time = date_time.astimezone(target_tz)

	return str(date_time)
