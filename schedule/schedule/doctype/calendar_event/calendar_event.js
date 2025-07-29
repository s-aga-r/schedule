// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Calendar Event", {
	refresh(frm) {
		frm.trigger("set_queries");
	},

	set_queries(frm) {
		frm.set_query("calendar", () => ({
			query: "schedule.utils.query.get_user_calendars",
			filters: {
				user: frm.doc.user,
			},
		}));
	},
});
