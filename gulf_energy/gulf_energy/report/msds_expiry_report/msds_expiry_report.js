// Copyright (c) 2026, sammish and contributors
// For license information, please see license.txt

frappe.query_reports["MSDS Expiry Report"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Draft", "Active", "Expired"],
			default: "Active",
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "expiring_within_days",
			label: __("Expiring Within (Days)"),
			fieldtype: "Int",
			default: 30,
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "status") {
			if (data.status === "Active") {
				value = `<span class="text-success font-weight-bold">${value}</span>`;
			} else if (data.status === "Expired") {
				value = `<span class="text-danger font-weight-bold">${value}</span>`;
			} else if (data.status === "Draft") {
				value = `<span class="text-warning">${value}</span>`;
			}
		}

		if (column.fieldname === "days_remaining") {
			if (data.days_remaining <= 0) {
				value = `<span class="text-danger font-weight-bold">${value}</span>`;
			} else if (data.days_remaining <= 30) {
				value = `<span class="text-warning font-weight-bold">${value}</span>`;
			} else {
				value = `<span class="text-success">${value}</span>`;
			}
		}

		if (column.fieldname === "is_hazardous" && data.is_hazardous) {
			value = `<span class="text-danger font-weight-bold">Yes</span>`;
		}

		return value;
	},
};
