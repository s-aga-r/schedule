# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from urllib.parse import unquote

import frappe
from caldav.calendarobjectresource import Event
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, convert_utc_to_system_timezone, now
from uuid_utils import uuid7

from frappe_calendar.calendar import get_caldav_client
from frappe_calendar.utils import convert_to_utc, extract_filter_values


class CalendarEvent(Document):
	def autoname(self) -> None:
		self.name = f"{self.calendar}|{uuid7()!s}"

	def db_insert(self, *args, **kwargs) -> None:
		attendees = [
			{"email": attendee.email, "cn": attendee.cn, "role": attendee.role} for attendee in self.attendees
		]
		event_data = {
			"dtstamp": convert_to_utc(now(), naive=True),
			"dtstart": convert_to_utc(self.dtstart, naive=True),
			"summary": self.summary,
			"description": self.description,
			"location": self.location,
			"attendees": attendees,
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

	def get_param(value: list | str, default: str | None = None) -> str | None:
		"""Extract the first value from a list or return the string value directly."""

		if isinstance(value, list):
			return str(value[0]) if value else default

		return str(value) if value else default

	def to_local_str(dt_value) -> str:
		"""Convert a datetime value to system timezone string."""

		return str(convert_utc_to_system_timezone(dt_value))

	vevent = event.vobject_instance.vevent
	calendar = f"{user}|{event.parent.id}"

	try:
		ical_raw = event.data.decode("utf-8") if isinstance(event.data, bytes) else str(event.data)
	except Exception:
		ical_raw = ""

	creation = to_local_str(getattr(getattr(vevent, "created", None), "value", vevent.dtstamp.value))
	modified = to_local_str(getattr(getattr(vevent, "last_modified", None), "value", vevent.dtstamp.value))

	formatted_event = {
		"user": user,
		"calendar": calendar,
		"uid": vevent.uid.value,
		"url": unquote(str(event.url)),
		"name": f"{calendar}|{vevent.uid.value}",
		"dtstart": to_local_str(vevent.dtstart.value),
		"ical_raw": ical_raw,
		"creation": creation,
		"modified": modified,
	}

	optional_fields = {
		"status": str,
		"summary": str,
		"location": str,
		"organizer": str,
		"description": str,
		"dtend": convert_utc_to_system_timezone,
	}
	for key, transform in optional_fields.items():
		field_obj = getattr(vevent, key, None)
		if field_obj and getattr(field_obj, "value", None):
			value = field_obj.value
			if key == "organizer":
				value = value.replace("mailto:", "")
			formatted_event[key] = str(transform(value))

	if not formatted_event.get("status"):
		formatted_event["status"] = "CONFIRMED"

	formatted_event["attendees"] = []
	for attendee in getattr(vevent, "attendee_list", []):
		formatted_event["attendees"].append(
			{
				"email": attendee.value.replace("mailto:", ""),
				"cn": get_param(attendee.params.get("CN")),
				"cutype": get_param(attendee.params.get("CUTYPE"), "INDIVIDUAL"),
				"role": get_param(attendee.params.get("ROLE"), "REQ-PARTICIPANT"),
				"partstat": get_param(attendee.params.get("PARTSTAT"), "NEEDS-ACTION"),
				"x_num_guests": cint(get_param(attendee.params.get("X-NUM-GUESTS"), "0")),
				"rsvp": 0 if get_param(attendee.params.get("RSVP")) == "FALSE" else 1,
			}
		)

	return formatted_event
