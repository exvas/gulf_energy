// Copyright (c) 2025, sammish and contributors
// For license information, please see license.txt

frappe.ui.form.on("Investor", {
	refresh(frm) {
		// Calculate converted amount if all required fields are present
		if (frm.doc.invested_amount && frm.doc.exchange_rate) {
			calculate_company_currency_amount(frm);
		}
		
		// Calculate dividend amount if fields are present
		if (frm.doc.invested_amount_company_currency && frm.doc.dividend) {
			calculate_dividend_amount(frm);
		}
		
		// Set filters for Amount Received Account
		set_amount_received_account_filter(frm);
		
		// Set filters for Project
		set_project_filter(frm);
		
		// Add validation message for submitting
		if (!frm.doc.__islocal && frm.doc.docstatus === 0) {
			frm.dashboard.add_comment(
				__('Note: Upon submission, an investor account will be created under "3110 - Investor Capital" and a journal entry will be generated.'),
				'blue', true
			);
		}
		
		// Add button to preview investor account name
		if (frm.doc.docstatus === 0 && frm.doc.investor_name && frm.doc.invested_company) {
			frm.add_custom_button(__('Preview Account Name'), function() {
				frappe.call({
					method: "gulf_energy.gulf_energy.doctype.investor.investor.preview_investor_account_name",
					args: {
						investor_name: frm.doc.investor_name,
						invested_company: frm.doc.invested_company,
						invested_project: frm.doc.invested_project || null
					},
					callback: function(r) {
						if (r.message) {
							frappe.msgprint({
								title: __('Investor Account Preview'),
								message: __('The investor account will be created as: <br><strong>{0}</strong>', [r.message]),
								indicator: 'blue'
							});
						}
					}
				});
			});
		}
	},

	before_submit(frm) {
		if (!frm.doc.invested_amount || !frm.doc.exchange_rate || !frm.doc.amount_received_account) {
			frappe.throw(__('Please ensure all required fields are filled before submitting.'));
		}
	},

	invested_currency(frm) {
		if (frm.doc.invested_currency && frm.doc.company_currency && frm.doc.invested_currency !== frm.doc.company_currency) {
			get_exchange_rate(frm);
		} else if (frm.doc.invested_currency === frm.doc.company_currency) {
			frm.set_value('exchange_rate', 1);
			calculate_company_currency_amount(frm);
		}
	},

	invested_amount(frm) {
		if (frm.doc.invested_amount && frm.doc.exchange_rate) {
			calculate_company_currency_amount(frm);
		}
	},

	exchange_rate(frm) {
		if (frm.doc.invested_amount && frm.doc.exchange_rate) {
			calculate_company_currency_amount(frm);
		}
	},

	dividend(frm) {
		// Validate dividend percentage
		if (frm.doc.dividend < 0) {
			frappe.msgprint(__('Dividend percentage cannot be negative'));
			frm.set_value('dividend', 0);
			return;
		}
		
		if (frm.doc.dividend > 100) {
			frappe.msgprint(__('Dividend percentage cannot exceed 100%'));
			frm.set_value('dividend', 100);
			return;
		}
		
		calculate_dividend_amount(frm);
	},

	invested_amount_company_currency(frm) {
		calculate_dividend_amount(frm);
	},

	investor_name(frm) {
		check_existing_account(frm);
	},

	invested_project(frm) {
		set_project_filter(frm);
		check_existing_account(frm);
	},

	invested_project(frm) {
		// Update preview when project changes - no need to call preview automatically
		// User can click the Preview Account Name button to see the updated name
	},

	invested_company(frm) {
		if (frm.doc.invested_currency && frm.doc.company_currency && frm.doc.invested_currency !== frm.doc.company_currency) {
			get_exchange_rate(frm);
		}
		// Update account and project filters when company changes
		set_amount_received_account_filter(frm);
		set_project_filter(frm);
	}
});

function set_amount_received_account_filter(frm) {
	if (frm.doc.invested_company) {
		frm.set_query("amount_received_account", function() {
			return {
				filters: {
					"company": frm.doc.invested_company,
					"account_type": ["in", ["Bank", "Cash"]],
					"is_group": 0
				}
			};
		});
	}
}

function set_project_filter(frm) {
	if (frm.doc.invested_company) {
		frm.set_query("invested_project", function() {
			return {
				filters: {
					"company": frm.doc.invested_company,
					"status": ["not in", ["Cancelled", "Completed"]]
				}
			};
		});
	}
}

function get_exchange_rate(frm) {
	if (frm.doc.invested_currency && frm.doc.company_currency && frm.doc.invested_currency !== frm.doc.company_currency) {
		frappe.call({
			method: "erpnext.setup.utils.get_exchange_rate",
			args: {
				from_currency: frm.doc.invested_currency,
				to_currency: frm.doc.company_currency,
				transaction_date: frm.doc.investe_date || frappe.datetime.get_today()
			},
			callback: function(r) {
				if (r.message) {
					frm.set_value('exchange_rate', r.message);
					calculate_company_currency_amount(frm);
					frappe.show_alert({
						message: __('Exchange rate updated from ERPNext Currency Exchange'),
						indicator: 'green'
					});
				} else {
					frappe.msgprint({
						title: __('Exchange Rate Not Found'),
						message: __('Exchange rate not found for {0} to {1}. Please enter manually.', [frm.doc.invested_currency, frm.doc.company_currency]),
						indicator: 'orange'
					});
					frm.set_value('exchange_rate', 1);
				}
			},
			error: function() {
				frappe.msgprint({
					title: __('Error'),
					message: __('Failed to fetch exchange rate. Please enter manually.'),
					indicator: 'red'
				});
				frm.set_value('exchange_rate', 1);
			}
		});
	}
}

function calculate_company_currency_amount(frm) {
	if (frm.doc.invested_amount && frm.doc.exchange_rate) {
		let converted_amount = flt(frm.doc.invested_amount) * flt(frm.doc.exchange_rate);
		frm.set_value('invested_amount_company_currency', converted_amount);
		
		// Calculate dividend amount when company currency amount changes
		calculate_dividend_amount(frm);
		
		// Show currency information in dashboard
		if (frm.doc.invested_currency && frm.doc.company_currency && frm.doc.invested_currency !== frm.doc.company_currency) {
			let message = __('Conversion: {0} {1} × {2} = {3} {4}', [
				format_currency(frm.doc.invested_amount, frm.doc.invested_currency),
				frm.doc.invested_currency,
				frm.doc.exchange_rate,
				format_currency(converted_amount, frm.doc.company_currency),
				frm.doc.company_currency
			]);
			
			frm.dashboard.clear_comment();
			frm.dashboard.add_comment(message, 'blue', true);
		}
	}
}

function calculate_dividend_amount(frm) {
	if (frm.doc.invested_amount_company_currency && frm.doc.dividend) {
		let dividend_amount = flt(frm.doc.invested_amount_company_currency) * flt(frm.doc.dividend) / 100;
		frm.set_value('eligable_dividend_amount_in_company_currency', dividend_amount);
		
		// Show dividend calculation info
		if (frm.doc.dividend > 0) {
			let dividend_message = __('Dividend Calculation: {0} × {1}% = {2}', [
				format_currency(frm.doc.invested_amount_company_currency, frm.doc.company_currency),
				frm.doc.dividend,
				format_currency(dividend_amount, frm.doc.company_currency)
			]);
			
			// Add dividend info to dashboard
			setTimeout(() => {
				frm.dashboard.add_comment(dividend_message, 'green', true);
			}, 100);
		}
	}
}

function check_existing_account(frm) {
	if (frm.doc.investor_name && frm.doc.invested_company && frm.doc.docstatus === 0) {
		frappe.call({
			method: "gulf_energy.gulf_energy.doctype.investor.investor.check_existing_investor_account",
			args: {
				investor_name: frm.doc.investor_name,
				invested_company: frm.doc.invested_company,
				invested_project: frm.doc.invested_project || null
			},
			callback: function(r) {
				if (r.message && r.message.exists) {
					frm.dashboard.add_comment(
						__('Note: Existing account found: <strong>{0}</strong> - This account will be reused for the investment.', 
						[r.message.account_name]), 
						'orange', true
					);
				} else if (r.message && !r.message.exists) {
					let account_name = r.message.new_account_name;
					frm.dashboard.add_comment(
						__('Note: New account will be created: <strong>{0}</strong>', [account_name]), 
						'blue', true
					);
				}
			}
		});
	}
}
