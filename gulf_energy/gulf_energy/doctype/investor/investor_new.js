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
				__('Note: Upon submission, an investor account will be created and journal entry will be automatically generated in the invested company.'),
				'blue', true
			);
		}
		
		// Add button to create manual journal entry for submitted documents
		if (frm.doc.docstatus === 1 && !frm.doc.journal_entry) {
			frm.add_custom_button(__('Create Manual Journal Entry'), function() {
				frappe.show_alert({
					message: __('Creating journal entry...'),
					indicator: 'blue'
				});
				
				frappe.call({
					method: "create_manual_journal_entry",
					doc: frm.doc,
					callback: function(r) {
						if (r.message && r.message.success) {
							frappe.msgprint({
								title: __('Success'),
								message: r.message.message,
								indicator: 'green'
							});
							frm.reload_doc();
						} else {
							frappe.msgprint({
								title: __('Error'),
								message: r.message ? r.message.error : 'Failed to create journal entry',
								indicator: 'red'
							});
						}
					},
					error: function(err) {
						frappe.msgprint({
							title: __('Error'),
							message: __('Failed to create manual journal entry: {0}', [err.message || 'Unknown error']),
							indicator: 'red'
						});
					}
				});
			}, __('Create'));
		}
		
		// Add button to preview investor account details
		if (frm.doc.docstatus === 0 && frm.doc.investor_name && frm.doc.invested_company) {
			frm.add_custom_button(__('Preview Account Structure'), function() {
				frappe.call({
					method: "preview_account_structure",
					doc: frm.doc,
					callback: function(r) {
						if (r.message) {
							let preview = r.message;
							let message = '';
							
							if (preview.error) {
								message = `<div class="text-danger"><strong>Error:</strong> ${preview.error}</div>`;
							} else if (preview.action === 'reuse') {
								message = `
									<div class="alert alert-info">
										<strong>Account Reuse:</strong><br>
										${preview.message}<br>
										<small>No new account will be created.</small>
									</div>
								`;
							} else if (preview.action === 'create') {
								let parent_info = preview.parent_status === 'exists' 
									? '<span class="text-success">✓ Parent account exists</span>'
									: '<span class="text-warning">⚠ Parent account will be created</span>';
								
								message = `
									<div class="alert alert-success">
										<strong>New Account Creation:</strong><br>
										<strong>Account Number:</strong> ${preview.account_number}<br>
										<strong>Account Name:</strong> ${preview.account_name}<br>
										<strong>Company:</strong> ${preview.company}<br>
										<strong>Parent Account:</strong> ${preview.parent_account}<br>
										${parent_info}
									</div>
								`;
							}
							
							frappe.msgprint({
								title: __('Account Structure Preview'),
								message: message,
								indicator: preview.error ? 'red' : 'blue'
							});
						}
					}
				});
			}, __('Preview'));
		}
		
		// Add button to manually fix account structure (for troubleshooting)
		if (frm.doc.docstatus === 0 && frm.doc.invested_company) {
			frm.add_custom_button(__('Fix Account Structure'), function() {
				frappe.call({
					method: "fix_account_structure",
					doc: frm.doc,
					callback: function(r) {
						if (r.message) {
							if (r.message.success) {
								frappe.msgprint({
									title: __('Account Structure Fixed'),
									message: `<div class="alert alert-success">
										<strong>Success!</strong><br>
										${r.message.message}<br>
										<small>Account: ${r.message.account || 'Created successfully'}</small>
									</div>`,
									indicator: 'green'
								});
								frm.reload_doc();
							} else {
								frappe.msgprint({
									title: __('Fix Failed'),
									message: `<div class="text-danger">
										<strong>Error:</strong> ${r.message.error}<br>
										<small>Please check if the account structure exists in Chart of Accounts.</small>
									</div>`,
									indicator: 'red'
								});
							}
						}
					}
				});
			}, __('Tools'));
		}
		
		// Add button to check company structure (simplified)
		if (frm.doc.docstatus === 0 && frm.doc.invested_company) {
			frm.add_custom_button(__('Check Company Structure'), function() {
				frappe.call({
					method: "gulf_energy.gulf_energy.doctype.investor.investor.get_company_structure_info",
					args: {
						company: frm.doc.invested_company
					},
					callback: function(r) {
						if (r.message) {
							let info = r.message;
							let message = '';
							
							if (info.error) {
								message = `<div class="text-danger"><strong>Error:</strong> ${info.error}</div>`;
							} else {
								message = `
									<div class="alert alert-info">
										<strong>Company Structure:</strong><br>
										<strong>Company:</strong> ${info.company}<br>
										<strong>Has Investor Capital:</strong> ${info.has_investor_capital ? '✅ Yes' : '❌ No'}<br>
										<small>All accounts will be created in: ${info.company}</small>
									</div>
								`;
							}
							
							frappe.msgprint({
								title: __('Company Structure'),
								message: message,
								indicator: info.error ? 'red' : 'blue'
							});
						}
					}
				});
			}, __('Tools'));
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

	invested_company(frm) {
		if (frm.doc.invested_currency && frm.doc.company_currency && frm.doc.invested_currency !== frm.doc.company_currency) {
			get_exchange_rate(frm);
		}
		// Update account and project filters when company changes
		set_amount_received_account_filter(frm);
		set_project_filter(frm);
		
		// Clear previous account warnings
		frm.dashboard.clear_comment();
	},

	amount_received_account(frm) {
		// Check for same company when account is selected
		if (frm.doc.amount_received_account && frm.doc.invested_company) {
			check_account_company_match(frm);
		}
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
		let invested_amount = flt(frm.doc.invested_amount);
		let exchange_rate = flt(frm.doc.exchange_rate);
		let converted_amount = flt(invested_amount * exchange_rate, 2);
		
		// Set the calculated value
		frm.set_value('invested_amount_company_currency', converted_amount);
		
		// Calculate dividend amount when company currency amount changes
		calculate_dividend_amount(frm);
		
		// Show currency information in dashboard
		if (frm.doc.invested_currency && frm.doc.company_currency && frm.doc.invested_currency !== frm.doc.company_currency) {
			let message = __('Conversion: {0} {1} × {2} = {3} {4}', [
				format_currency(invested_amount, frm.doc.invested_currency),
				frm.doc.invested_currency,
				exchange_rate,
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
					let company = r.message.company;
					
					let message = __('Note: New account will be created: <strong>{0}</strong> in company <strong>{1}</strong>', 
						[account_name, company]);
					
					frm.dashboard.add_comment(message, 'blue', true);
				}
			}
		});
	}
}

function check_account_company_match(frm) {
	if (frm.doc.amount_received_account && frm.doc.invested_company) {
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Account",
				name: frm.doc.amount_received_account,
				fieldname: ["company", "account_type"]
			},
			callback: function(r) {
				if (r.message) {
					let account_company = r.message.company;
					
					// Check if account belongs to different company
					if (account_company !== frm.doc.invested_company) {
						frm.dashboard.add_comment(
							__('⚠️ Warning: Selected bank account belongs to <strong>{0}</strong>, but investment is for <strong>{1}</strong>. Please select a bank account from the invested company.', 
							[account_company, frm.doc.invested_company]), 
							'red', true
						);
					} else {
						frm.dashboard.add_comment(
							__('✅ Perfect: Bank account and investment are both in <strong>{0}</strong>.', 
							[frm.doc.invested_company]), 
							'green', true
						);
					}
				}
			}
		});
	}
}
