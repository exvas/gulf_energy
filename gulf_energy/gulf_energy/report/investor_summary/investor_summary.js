// Copyright (c) 2025, sammish and contributors
// For license information, please see license.txt

frappe.query_reports["Investor Summary"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "investor_name",
			"label": __("Investor Name"),
			"fieldtype": "Data"
		},
		{
			"fieldname": "country",
			"label": __("Country"),
			"fieldtype": "Link",
			"options": "Country"
		},
		{
			"fieldname": "invested_project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project"
		},
		{
			"fieldname": "invested_currency",
			"label": __("Currency"),
			"fieldtype": "Link",
			"options": "Currency"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": ["", "Draft", "Submitted", "Cancelled"],
			"default": "Submitted"
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Highlight different statuses with colors
		if (column.fieldname == "docstatus") {
			if (value === "Draft") {
				value = `<span class="text-warning">${value}</span>`;
			} else if (value === "Submitted") {
				value = `<span class="text-success">${value}</span>`;
			} else if (value === "Cancelled") {
				value = `<span class="text-danger">${value}</span>`;
			}
		}
		
		// Format currency values with proper styling
		if (column.fieldname == "invested_amount" || 
			column.fieldname == "invested_amount_company_currency" || 
			column.fieldname == "eligable_dividend_amount_in_company_currency") {
			if (value && parseFloat(value) > 0) {
				value = `<span class="text-success font-weight-bold">${value}</span>`;
			}
		}
		
		// Highlight dividend percentage
		if (column.fieldname == "dividend" && value && parseFloat(value) > 0) {
			value = `<span class="text-primary font-weight-bold">${value}%</span>`;
		}
		
		return value;
	},
	
	"get_chart_data": function(columns, result) {
		return {
			data: {
				labels: result.map(d => d.investor_name || d.name),
				datasets: [
					{
						label: 'Investment Amount (Company Currency)',
						values: result.map(d => d.invested_amount_company_currency || 0)
					},
					{
						label: 'Eligible Dividend Amount',
						values: result.map(d => d.eligable_dividend_amount_in_company_currency || 0)
					}
				]
			},
			type: 'bar',
			height: 300,
			colors: ['#5e64ff', '#743ee2']
		};
	}
};
