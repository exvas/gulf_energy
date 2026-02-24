// Copyright (c) 2026, sammish and contributors
// For license information, please see license.txt

frappe.query_reports["Export Compliance Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -3),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "shipment_type",
			label: __("Shipment Type"),
			fieldtype: "Select",
			options: ["", "Sea", "Air", "Land"],
		},
		{
			fieldname: "compliance_status",
			label: __("Compliance Status"),
			fieldtype: "Select",
			options: ["", "Pending", "Partial", "Complete"],
		},
		{
			fieldname: "shipping_line",
			label: __("Shipping Line"),
			fieldtype: "Data",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "compliance_status") {
			if (data.compliance_status === "Complete") {
				value = `<span class="text-success font-weight-bold">${value}</span>`;
			} else if (data.compliance_status === "Partial") {
				value = `<span class="text-warning font-weight-bold">${value}</span>`;
			} else if (data.compliance_status === "Pending") {
				value = `<span class="text-danger font-weight-bold">${value}</span>`;
			}
		}

		if (column.fieldname === "workflow_state") {
			if (data.workflow_state === "Approved" || data.workflow_state === "Submitted") {
				value = `<span class="text-success">${value}</span>`;
			} else if (data.workflow_state === "Rejected") {
				value = `<span class="text-danger">${value}</span>`;
			} else if (data.workflow_state === "Pending Review") {
				value = `<span class="text-warning">${value}</span>`;
			}
		}

		return value;
	},
};
