// Copyright (c) 2025, sammish and contributors
// For license information, please see license.txt

frappe.query_reports["Project Investment Summary"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 0
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 0
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 0
		},
		{
			"fieldname": "invested_project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"reqd": 0
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		// Format currency values
		if (column.fieldname === "total_investment" || column.fieldname === "total_dividend") {
			if (value) {
				return `<span style="font-weight: bold; color: #2e7d32;">${format_currency(value, data.company_currency)}</span>`;
			}
		}
		
		// Format percentage
		if (column.fieldname === "avg_dividend_percent") {
			if (value) {
				return `<span style="color: #1976d2;">${value}%</span>`;
			}
		}
		
		// Highlight project names
		if (column.fieldname === "project_name") {
			return `<span style="font-weight: bold; color: #424242;">${value}</span>`;
		}
		
		// Color code investor count
		if (column.fieldname === "total_investors") {
			let color = value >= 10 ? "#4caf50" : value >= 5 ? "#ff9800" : "#f44336";
			return `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
		}
		
		return default_formatter(value, row, column, data);
	},
	
	"onload": function(report) {
		// Add refresh button
		report.page.add_inner_button(__('Refresh'), function() {
			report.refresh();
		});
	}
};
