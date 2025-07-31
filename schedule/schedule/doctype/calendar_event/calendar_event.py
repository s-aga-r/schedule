# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from urllib.parse import unquote

import frappe
from caldav.calendarobjectresource import Event
from frappe import _
from frappe.model.document import Document
from frappe.utils import convert_utc_to_system_timezone, now
from uuid_utils import uuid7

from schedule.calendar import get_caldav_client
from schedule.utils import convert_to_utc, extract_filter_values


class CalendarEvent(Document):
	def autoname(self) -> None:
		self.name = f"{self.calendar}|{uuid7()!s}"

	def db_insert(self, *args, **kwargs) -> None:
		event_data = {
			"dtstamp": convert_to_utc(now(), naive=True),
			"dtstart": convert_to_utc(self.dtstart, naive=True),
			"summary": self.summary,
			"description": self.description,
			"location": self.location,
		}
		if self.dtend:
			event_data["dtend"] = convert_to_utc(self.dtend, naive=True)

		add_event(self.name, event_data)

	def load_from_db(self) -> "CalendarEvent":
		event = get_event(self.name)
		return super(Document, self).__init__(event)

	def db_update(self) -> None:
		updated_data = {
			"dtstamp": convert_to_utc(now(), naive=True),
			"dtstart": convert_to_utc(self.dtstart, naive=True),
			"summary": self.summary,
			"description": self.description,
			"location": self.location,
		}
		if self.dtend:
			updated_data["dtend"] = convert_to_utc(self.dtend, naive=True)

		update_event(self.name, updated_data)

	def delete(self) -> None:
		delete_event(self.name)

	@staticmethod
	def get_list(filters=None, page_length=20, **kwargs) -> list:
		filters = filters or []
		user_values = extract_filter_values(filters, [{"user": "="}])
		user = user_values[0] if user_values and user_values[0] else frappe.session.user

		if not user or user in ["Administrator", "Guest"]:
			frappe.msgprint(_("Please select a user to view events."), alert=True)
			return []

		events = fetch_events(user, limit=page_length)
		if not events:
			frappe.msgprint(_("No events found."), alert=True)

		return events

	@staticmethod
	def get_count(filters=None, **kwargs) -> int:
		return len(CalendarEvent.get_list(filters, **kwargs))

	@staticmethod
	def get_stats(**kwargs) -> dict:
		return {}


def add_event(name: str, event_data: dict) -> None:
	"""Adds a calendar event for the given user and calendar."""

	user, cal_id, event_uid = name.split("|")
	event_data["uid"] = event_uid
	client = get_caldav_client(user)
	calendar = client.get_calendar(cal_id, raise_exception=True)
	client.add_event(calendar, event_data)


def get_event(name: str) -> Event:
	"""Returns a calendar event for the given name."""

	user, cal_id, event_uid = name.split("|")
	client = get_caldav_client(user)
	calendar = client.get_calendar(cal_id, raise_exception=True)
	event = client.get_event(calendar, event_uid, raise_exception=True)
	return format_event(user, event)


def update_event(name: str, updated_data: dict) -> None:
	"""Updates a calendar event by its name."""

	user, cal_id, event_uid = name.split("|")
	client = get_caldav_client(user)
	calendar = client.get_calendar(cal_id, raise_exception=True)
	client.update_event(updated_data, calendar=calendar, event_uid=event_uid)


def delete_event(name: str) -> None:
	"""Deletes a calendar event by its name."""

	user, cal_id, event_uid = name.split("|")
	client = get_caldav_client(user)
	calendar = client.get_calendar(cal_id, raise_exception=True)
	client.delete_event(calendar=calendar, event_uid=event_uid)


def fetch_events(user: str, page: int = 1, limit: int = 10) -> list:
	"""Returns a list of calendar events for the given user."""

	result = []
	client = get_caldav_client(user)

	if calendars := client.get_calendars():
		for calendar in calendars:
			if events := client.get_events(calendar):
				result.extend([format_event(user, event) for event in events])

	return result


def format_event(user: str, event: Event) -> dict:
	"""Returns a formatted event dictionary for the given user and event."""

	vevent = event.vobject_instance.vevent
	calendar = f"{user}|{event.parent.id}"

	formatted_event = {
		"user": user,
		"calendar": calendar,
		"uid": vevent.uid.value,
		"url": unquote(str(event.url)),
		"name": f"{calendar}|{vevent.uid.value}",
		"dtstart": str(convert_utc_to_system_timezone(vevent.dtstart.value)),
		"creation": str(convert_utc_to_system_timezone(vevent.dtstamp.value)),
		"modified": str(convert_utc_to_system_timezone(vevent.dtstamp.value)),
	}

	optional_keys = {
		"summary": str,
		"description": str,
		"dtend": convert_utc_to_system_timezone,
	}
	for key, transform in optional_keys.items():
		value = getattr(vevent, key, None)
		if value and getattr(value, "value", None):
			formatted_event[key] = str(transform(value.value))

	return formatted_event
