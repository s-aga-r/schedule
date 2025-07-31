from datetime import datetime

import frappe
import vobject
from caldav import DAVClient
from caldav.calendarobjectresource import Event
from caldav.collection import Calendar
from caldav.lib.error import NotFoundError
from frappe import _
from frappe.utils import now

from schedule.utils import convert_to_utc


class CalDAVClient:
	"""Wrapper for caldav.DAVClient to interact with CalDAV servers."""

	def __init__(self, **kwargs) -> None:
		"""Initialize the CalDAV client."""

		self.client = DAVClient(**kwargs)

	def get_calendars(self) -> list[Calendar]:
		"""Returns a list of calendars from the CalDAV server."""

		principal = self.client.principal()
		return principal.calendars()

	def add_calendar(self, name: str, cal_id: str | None = None) -> Calendar:
		"""Creates a new calendar on the CalDAV server."""

		principal = self.client.principal()
		return principal.make_calendar(name, cal_id=cal_id)

	def get_calendar(self, cal_id: str, raise_exception: bool = False) -> Calendar:
		"""Returns a calendar by its ID from the CalDAV server."""

		for calendar in self.get_calendars():
			if calendar.id == cal_id:
				return calendar

		if raise_exception:
			frappe.throw(_("Calendar with ID {0} not found.").format(cal_id))

	def delete_calendar(self, calendar: Calendar | None = None, cal_id: str | None = None) -> None:
		"""Deletes a calendar from the CalDAV server by its instance or ID."""

		if not calendar:
			if not cal_id:
				frappe.throw(_("Either calendar or cal_id must be provided for deleting a calendar."))

			calendar = self.get_calendar(cal_id, raise_exception=True)

		calendar.delete()

	def get_events(self, calendar: Calendar) -> list[Event]:
		"""Returns a list of events from a specified calendar."""

		try:
			return calendar.events()
		except NotFoundError:
			return []

	def get_events_between(self, calendar: Calendar, start: datetime, end: datetime) -> list[Event]:
		"""Returns events in the calendar within a time range."""

		return calendar.date_search(start=start, end=end)

	def add_event(self, calendar: Calendar, event_data: dict) -> str:
		"""Creates a new event in a specified calendar."""

		cal = vobject.iCalendar()
		vevent = cal.add("vevent")

		for key, value in event_data.items():
			if key == "attendees" and isinstance(value, list):
				for att in value:
					attendee = vevent.add("attendee")
					attendee.value = f"mailto:{att['email']}"

					if att.get("cn"):
						attendee.params["CN"] = att["cn"]
					if att.get("role"):
						attendee.params["ROLE"] = att["role"]

					attendee.params["PARTSTAT"] = att.get("partstat", "NEEDS-ACTION")
					attendee.params["RSVP"] = att.get("rsvp", "TRUE")
			elif value is not None:
				vevent.add(key).value = value

		calendar.add_event(vevent.serialize())
		return event_data["uid"]

	def get_event(self, calendar: Calendar, event_uid: str, raise_exception: bool = False) -> Event | None:
		"""Returns an event from a specified calendar by its UID."""

		try:
			return calendar.event_by_uid(event_uid)
		except NotFoundError:
			if raise_exception:
				frappe.throw(
					_("Event with UID {0} not found in calendar {1}.").format(event_uid, calendar.name)
				)

	def update_event(
		self,
		updated_data: dict,
		event: Event | None = None,
		calendar: Calendar | None = None,
		event_uid: str | None = None,
	) -> None:
		"""Updates an existing event in a specified calendar by its instance or UID."""

		if not event:
			if not calendar or not event_uid:
				frappe.throw(
					_("Either event or both calendar and event_uid must be provided for updating an event.")
				)

			event = self.get_event(calendar, event_uid, raise_exception=True)

		updated_data.pop("uid", None)
		updated_data["dtstamp"] = convert_to_utc(now(), naive=True)

		vobj = event.vobject_instance
		vevent = vobj.vevent
		for key, value in updated_data.items():
			if value is None:
				continue
			elif hasattr(vevent, key):
				vevent_contents = getattr(vevent, key)
				if hasattr(vevent_contents, "value"):
					vevent_contents.value = value
				else:
					setattr(vevent, key, value)
			else:
				vevent.add(key).value = value

		event._vobject_instance = vobj
		event.save()

	def delete_event(
		self, event: Event | None = None, calendar: Calendar | None = None, event_uid: str | None = None
	) -> None:
		"""Deletes an existing event from a specified calendar by its instance or UID."""

		if not event:
			if not calendar or not event_uid:
				frappe.throw(
					_("Either event or both calendar and event_uid must be provided for deleting an event.")
				)

			event = self.get_event(calendar, event_uid, raise_exception=True)

		event.delete()


def get_caldav_client(user: str) -> CalDAVClient:
	"""Returns a CalDAV client for the given user."""

	user = frappe.get_doc("Mail Account", user)
	return CalDAVClient(
		url="http://localhost:8080/.well-known/caldav",
		auth=(user.name, user.get_password()),
	)
