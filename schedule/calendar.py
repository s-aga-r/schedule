import frappe
import vobject
from caldav import DAVClient
from caldav.calendarobjectresource import Event
from caldav.collection import Calendar
from frappe import _
from uuid_utils import uuid7


class CalDAVClient:
	"""Wrapper for caldav.DAVClient to interact with CalDAV servers."""

	def __init__(self, **kwargs) -> None:
		"""Initialize the CalDAV client."""

		self.client = DAVClient(**kwargs)

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

	def get_calendars(self) -> list[Calendar]:
		"""Returns a list of calendars from the CalDAV server."""

		principal = self.client.principal()
		return principal.calendars()

	def delete_calendar(self, calendar: Calendar | None = None, cal_id: str | None = None) -> None:
		"""Deletes a calendar from the CalDAV server by its instance or ID."""

		if not calendar:
			if not cal_id:
				frappe.throw(_("Either calendar or cal_id must be provided for deleting a calendar."))

			calendar = self.get_calendar(cal_id, raise_exception=True)

		calendar.delete()

	def add_event(self, calendar: Calendar, event_data: dict) -> str:
		"""Creates a new event in a specified calendar."""

		cal = vobject.iCalendar()
		event = cal.add("vevent")

		event_data["uid"] = str(uuid7())

		for key, value in event_data.items():
			event.add(key).value = value

		calendar.add_event(event.serialize())

		return event_data["uid"]

	def get_event(self, calendar: Calendar, event_uid: str, raise_exception: bool = False) -> Event | None:
		"""Returns an event from a specified calendar by its UID."""

		event_uid = event_uid.replace(".ics", "")

		for event in calendar.events():
			vevent = event.vobject_instance.vevent
			if hasattr(vevent, "uid") and vevent.uid.value == event_uid:
				return event

		if raise_exception:
			frappe.throw(_("Event with UID {0} not found in calendar {1}.").format(event_uid, calendar.name))

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

		for key, value in updated_data.items():
			if hasattr(event.vevent, key):
				setattr(event.vevent, key, value)
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
