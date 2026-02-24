# Copyright (c) 2026, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today, date_diff, add_days


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{
			"label": _("MSDS ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "MSDS Register",
			"width": 140,
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Version"),
			"fieldname": "version",
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Valid From"),
			"fieldname": "valid_from",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Expiry Date"),
			"fieldname": "expiry_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Days Remaining"),
			"fieldname": "days_remaining",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Approved By"),
			"fieldname": "approved_by",
			"fieldtype": "Link",
			"options": "User",
			"width": 150,
		},
		{
			"label": _("Is Hazardous"),
			"fieldname": "is_hazardous",
			"fieldtype": "Check",
			"width": 100,
		},
		{
			"label": _("Remarks"),
			"fieldname": "remarks",
			"fieldtype": "Data",
			"width": 200,
		},
	]


def get_data(filters):
	conditions = ["1=1"]

	if filters.get("status"):
		conditions.append("msds.status = %(status)s")
	if filters.get("item_code"):
		conditions.append("msds.item_code = %(item_code)s")

	# Handle "expiring within days" filter
	expiry_filter = ""
	if filters.get("expiring_within_days"):
		days = int(filters["expiring_within_days"])
		cutoff_date = add_days(today(), days)
		expiry_filter = f"AND msds.expiry_date <= '{cutoff_date}' AND msds.expiry_date >= '{today()}'"
		# Only show Active records for expiry warning
		conditions.append("msds.status = 'Active'")

	where_clause = " AND ".join(conditions)

	data = frappe.db.sql(
		f"""
		SELECT
			msds.name,
			msds.item_code,
			msds.item_name,
			msds.version,
			msds.status,
			msds.valid_from,
			msds.expiry_date,
			msds.approved_by,
			msds.remarks,
			item.custom_is_hazardous as is_hazardous
		FROM
			`tabMSDS Register` msds
		LEFT JOIN
			`tabItem` item ON msds.item_code = item.name
		WHERE
			{where_clause}
			{expiry_filter}
		ORDER BY
			msds.expiry_date ASC
		""",
		filters,
		as_dict=1,
	)

	# Calculate days remaining
	today_date = getdate(today())
	for row in data:
		if row.expiry_date:
			row.days_remaining = date_diff(row.expiry_date, today_date)
		else:
			row.days_remaining = 0

	return data
