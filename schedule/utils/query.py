import frappe

from schedule.schedule.doctype.calendar.calendar import fetch_calendars


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_user_calendars(
	doctype: str | None = None,
	txt: str | None = None,
	searchfield: str | None = None,
	start: int = 0,
	page_len: int = 20,
	filters: dict | None = None,
) -> list:
	"""Returns a list of calendars for the user."""

	filters = filters or {}
	user = filters.get("user", frappe.session.user)

	result = []
	if calendars := fetch_calendars(user):
		for calendar in calendars:
			if txt and txt.lower() not in calendar["name"].lower():
				continue

			result.append([calendar["name"]])

	return result[start : start + page_len]
