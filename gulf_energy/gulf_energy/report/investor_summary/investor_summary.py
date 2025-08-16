# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, fmt_money

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
			"label": _("Investor ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Investor",
			"width": 120
		},
		{
			"label": _("Investor Name"),
			"fieldname": "investor_name",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Country"),
			"fieldname": "country",
			"fieldtype": "Link",
			"options": "Country",
			"width": 100
		},
		{
			"label": _("Investment Date"),
			"fieldname": "investe_date",
			"fieldtype": "Date",
			"width": 120
		},
		{
			"label": _("Project"),
			"fieldname": "invested_project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 120
		},
		{
			"label": _("Project Name"),
			"fieldname": "project_name",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Invested Currency"),
			"fieldname": "invested_currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 100
		},
		{
			"label": _("Invested Amount"),
			"fieldname": "invested_amount",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"label": _("Exchange Rate"),
			"fieldname": "exchange_rate",
			"fieldtype": "Float",
			"width": 120,
			"precision": 6
		},
		{
			"label": _("Amount (Company Currency)"),
			"fieldname": "invested_amount_company_currency",
			"fieldtype": "Currency",
			"width": 160
		},
		{
			"label": _("Company Currency"),
			"fieldname": "company_currency",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Dividend %"),
			"fieldname": "dividend",
			"fieldtype": "Percent",
			"width": 100
		},
		{
			"label": _("Eligible Dividend Amount"),
			"fieldname": "eligable_dividend_amount_in_company_currency",
			"fieldtype": "Currency",
			"width": 160
		},
		{
			"label": _("Dividend Return Date"),
			"fieldname": "dividend_return_date",
			"fieldtype": "Date",
			"width": 140
		},
		{
			"label": _("Investor Account"),
			"fieldname": "investor_account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 200
		},
		{
			"label": _("Journal Entry"),
			"fieldname": "journal_entry",
			"fieldtype": "Link",
			"options": "Journal Entry",
			"width": 140
		},
		{
			"label": _("Status"),
			"fieldname": "docstatus",
			"fieldtype": "Data",
			"width": 100
		}
	]
	return columns

def get_data(filters):
	"""Get investor data based on filters"""
	conditions = get_conditions(filters)
	
	data = frappe.db.sql(f"""
		SELECT
			inv.name,
			inv.investor_name,
			inv.country,
			inv.investe_date,
			inv.invested_project,
			inv.project_name,
			inv.invested_currency,
			inv.invested_amount,
			inv.exchange_rate,
			inv.invested_amount_company_currency,
			inv.company_currency,
			inv.dividend,
			inv.eligable_dividend_amount_in_company_currency,
			inv.dividend_return_date,
			inv.investor_account,
			inv.journal_entry,
			CASE 
				WHEN inv.docstatus = 0 THEN 'Draft'
				WHEN inv.docstatus = 1 THEN 'Submitted'
				WHEN inv.docstatus = 2 THEN 'Cancelled'
			END as docstatus
		FROM 
			`tabInvestor` inv
		WHERE 
			{conditions}
		ORDER BY 
			inv.investe_date DESC, inv.creation DESC
	""", filters, as_dict=1)
	
	# Format currency values
	for row in data:
		if row.invested_amount:
			row.invested_amount = flt(row.invested_amount, 2)
		if row.invested_amount_company_currency:
			row.invested_amount_company_currency = flt(row.invested_amount_company_currency, 2)
		if row.eligable_dividend_amount_in_company_currency:
			row.eligable_dividend_amount_in_company_currency = flt(row.eligable_dividend_amount_in_company_currency, 2)
		if row.exchange_rate:
			row.exchange_rate = flt(row.exchange_rate, 6)
		if row.dividend:
			row.dividend = flt(row.dividend, 2)
	
	return data

def get_conditions(filters):
	"""Build SQL conditions based on filters"""
	conditions = ["inv.docstatus <= 2"]  # Include all statuses by default
	
	if filters.get("company"):
		conditions.append("inv.invested_company = %(company)s")
	
	if filters.get("from_date"):
		conditions.append("inv.investe_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("inv.investe_date <= %(to_date)s")
	
	if filters.get("investor_name"):
		conditions.append("inv.investor_name LIKE %(investor_name)s")
		filters["investor_name"] = f"%{filters.get('investor_name')}%"
	
	if filters.get("country"):
		conditions.append("inv.country = %(country)s")
	
	if filters.get("invested_project"):
		conditions.append("inv.invested_project = %(invested_project)s")
	
	if filters.get("invested_currency"):
		conditions.append("inv.invested_currency = %(invested_currency)s")
	
	if filters.get("status"):
		if filters.get("status") == "Draft":
			conditions.append("inv.docstatus = 0")
		elif filters.get("status") == "Submitted":
			conditions.append("inv.docstatus = 1")
		elif filters.get("status") == "Cancelled":
			conditions.append("inv.docstatus = 2")
	
	return " AND ".join(conditions)
