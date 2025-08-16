# Copyright (c) 2025, sammish and contributors
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
	"""Define report columns"""
	columns = [
		{
			"label": _("Project Code"),
			"fieldname": "invested_project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 120
		},
		{
			"label": _("Project Name"),
			"fieldname": "project_name",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Company"),
			"fieldname": "invested_company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 150
		},
		{
			"label": _("Total Investors"),
			"fieldname": "total_investors",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("Total Investment (Company Currency)"),
			"fieldname": "total_investment",
			"fieldtype": "Currency",
			"width": 200
		},
		{
			"label": _("Total Eligible Dividend"),
			"fieldname": "total_dividend",
			"fieldtype": "Currency",
			"width": 180
		},
		{
			"label": _("Average Dividend %"),
			"fieldname": "avg_dividend_percent",
			"fieldtype": "Percent",
			"width": 140
		},
		{
			"label": _("Currency"),
			"fieldname": "company_currency",
			"fieldtype": "Data",
			"width": 100
		}
	]
	return columns

def get_data(filters):
	"""Get project-wise investment summary"""
	conditions = get_conditions(filters)
	
	data = frappe.db.sql(f"""
		SELECT
			inv.invested_project,
			MAX(inv.project_name) as project_name,
			inv.invested_company,
			COUNT(DISTINCT inv.name) as total_investors,
			SUM(inv.invested_amount_company_currency) as total_investment,
			SUM(inv.eligable_dividend_amount_in_company_currency) as total_dividend,
			AVG(inv.dividend) as avg_dividend_percent,
			MAX(inv.company_currency) as company_currency
		FROM 
			`tabInvestor` inv
		WHERE 
			{conditions}
			AND inv.invested_project IS NOT NULL
			AND inv.invested_project != ''
		GROUP BY 
			inv.invested_project, inv.invested_company
		ORDER BY 
			total_investment DESC
	""", filters, as_dict=1)
	
	# Format values
	for row in data:
		if row.total_investment:
			row.total_investment = flt(row.total_investment, 2)
		if row.total_dividend:
			row.total_dividend = flt(row.total_dividend, 2)
		if row.avg_dividend_percent:
			row.avg_dividend_percent = flt(row.avg_dividend_percent, 2)
	
	return data

def get_conditions(filters):
	"""Build SQL conditions based on filters"""
	conditions = ["inv.docstatus = 1"]  # Only submitted records
	
	if filters.get("company"):
		conditions.append("inv.invested_company = %(company)s")
	
	if filters.get("from_date"):
		conditions.append("inv.investe_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("inv.investe_date <= %(to_date)s")
	
	if filters.get("invested_project"):
		conditions.append("inv.invested_project = %(invested_project)s")
	
	return " AND ".join(conditions)
