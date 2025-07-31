# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from urllib.parse import unquote

import frappe
from frappe import _
from frappe.model.document import Document
from uuid_utils import uuid7

from schedule.calendar import get_caldav_client
from schedule.utils import extract_filter_values


class Calendar(Document):
	def autoname(self) -> None:
		self.name = f"{self.user}|{uuid7()!s}"

	def db_insert(self, *args, **kwargs) -> None:
		add_calendar(self.name, self._name)

	def load_from_db(self) -> "Calendar":
		calendar = get_calendar(self.name)
		return super(Document, self).__init__(calendar)

	def db_update(self) -> None:
		raise NotImplementedError

	def delete(self) -> None:
		delete_calendar(self.name)

	@staticmethod
	def get_list(filters=None, page_length=20, **kwargs) -> list:
		filters = filters or []
		user_values = extract_filter_values(filters, [{"user": "="}])
		user = user_values[0] if user_values and user_values[0] else frappe.session.user

		if not user or user in ["Administrator", "Guest"]:
			frappe.msgprint(_("Please select a user to view calendars."), alert=True)
			return []

		calendars = fetch_calendars(user, limit=page_length)

		if not calendars:
			frappe.msgprint(_("No calendars found."), alert=True)

		return calendars

	@staticmethod
	def get_count(filters=None, **kwargs) -> int:
		return len(Calendar.get_list(filters, **kwargs))

	@staticmethod
	def get_stats(**kwargs) -> dict:
		return {}


def add_calendar(name: str, cal_name: str | None = None) -> None:
	"""Adds a calendar for the given user."""

	user, cal_id = name.split("|")
	client = get_caldav_client(user)
	client.add_calendar(cal_name, cal_id)


def get_calendar(name: str) -> dict:
	"""Returns a calendar for the given name."""

	user, cal_id = name.split("|")
	client = get_caldav_client(user)
	if calendar := client.get_calendar(cal_id, raise_exception=True):
		return format_calendar(user, calendar)


def delete_calendar(name: str) -> None:
	"""Deletes a calendar for the given user by its ID."""

	user, cal_id = name.split("|")
	client = get_caldav_client(user)
	client.delete_calendar(cal_id=cal_id)


def fetch_calendars(user: str, page: int = 1, limit: int = 10) -> list:
	"""Returns a list of calendars for the given user."""

	client = get_caldav_client(user)
	if calendars := client.get_calendars():
		return [format_calendar(user, calendar) for calendar in calendars]

	return []


def format_calendar(user: str, calendar: Calendar) -> dict:
	"""Returns a formatted calendar dictionary."""

	return {
		"user": user,
		"_name": calendar.name,
		"name": f"{user}|{calendar.id}",
		"url": unquote(str(calendar.url)),
	}
