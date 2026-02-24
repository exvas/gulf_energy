# Copyright (c) 2026, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{
			"label": _("ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Export Shipment Compliance",
			"width": 160,
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 150,
		},
		{
			"label": _("Shipment Type"),
			"fieldname": "shipment_type",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("B/L Number"),
			"fieldname": "bl_number",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Shipping Line"),
			"fieldname": "shipping_line",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Vessel"),
			"fieldname": "vessel_name",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Port of Loading"),
			"fieldname": "port_of_loading",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Port of Discharge"),
			"fieldname": "port_of_discharge",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Origin"),
			"fieldname": "country_of_origin",
			"fieldtype": "Link",
			"options": "Country",
			"width": 100,
		},
		{
			"label": _("Destination"),
			"fieldname": "country_of_destination",
			"fieldtype": "Link",
			"options": "Country",
			"width": 100,
		},
		{
			"label": _("Containers"),
			"fieldname": "total_containers",
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"label": _("Gross Weight (KG)"),
			"fieldname": "total_gross_weight",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"label": _("Compliance"),
			"fieldname": "compliance_status",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Status"),
			"fieldname": "workflow_state",
			"fieldtype": "Data",
			"width": 120,
		},
	]


def get_data(filters):
	conditions = ["esc.docstatus < 2"]

	if filters.get("company"):
		conditions.append("esc.company = %(company)s")
	if filters.get("from_date"):
		conditions.append("esc.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("esc.posting_date <= %(to_date)s")
	if filters.get("shipment_type"):
		conditions.append("esc.shipment_type = %(shipment_type)s")
	if filters.get("compliance_status"):
		conditions.append("esc.compliance_status = %(compliance_status)s")
	if filters.get("shipping_line"):
		conditions.append("esc.shipping_line LIKE %(shipping_line)s")
		filters["shipping_line"] = f"%{filters.get('shipping_line')}%"

	where_clause = " AND ".join(conditions)

	data = frappe.db.sql(
		f"""
		SELECT
			esc.name,
			esc.posting_date,
			esc.company,
			esc.shipment_type,
			esc.bl_number,
			esc.shipping_line,
			esc.vessel_name,
			esc.port_of_loading,
			esc.port_of_discharge,
			esc.country_of_origin,
			esc.country_of_destination,
			esc.total_containers,
			esc.total_gross_weight,
			esc.compliance_status,
			esc.workflow_state
		FROM
			`tabExport Shipment Compliance` esc
		WHERE
			{where_clause}
		ORDER BY
			esc.posting_date DESC, esc.creation DESC
		""",
		filters,
		as_dict=1,
	)

	for row in data:
		if row.total_gross_weight:
			row.total_gross_weight = flt(row.total_gross_weight, 2)

	return data
