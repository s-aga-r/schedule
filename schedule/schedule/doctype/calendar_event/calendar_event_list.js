frappe.listview_settings["Calendar Event"] = {
	get_indicator: (doc) => {
		const status_colors = {
			TENTATIVE: "blue",
			CONFIRMED: "green",
			CANCELLED: "red",
		};
		return [__(doc.status), status_colors[doc.status], "status,=," + doc.status];
	},
};
