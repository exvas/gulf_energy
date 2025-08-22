// Copyright (c) 2025, sammish and contributors
// Complete Investor.js - Full Featured with Safe Save Logic

frappe.ui.form.on("Investor", {
	setup(frm) {
		// Setup filters only once during form initialization
		frm.set_query("amount_received_account", function() {
			if (frm.doc.invested_company) {
				return {
					filters: {
						"company": frm.doc.invested_company,
						"account_type": ["in", ["Bank", "Cash"]],
						"is_group": 0
					}
				};
			}
		});
		
		frm.set_query("invested_project", function() {
			if (frm.doc.invested_company) {
				return {
					filters: {
						"company": frm.doc.invested_company,
						"status": ["not in", ["Cancelled", "Completed"]]
					}
				};
			}
		});
	},

	refresh(frm) {
		// Clear any existing dashboard comments
		frm.dashboard.clear_comment();
		
		// Add submission note for draft documents
		if (!frm.doc.__islocal && frm.doc.docstatus === 0) {
			frm.dashboard.add_comment(
				__('Note: Upon submission, an investor account will be created and journal entry can be created manually.'),
				'blue', true
			);
		}
		
		// Add buttons based on document status
		add_custom_buttons(frm);
		
		// Show calculation info if available
		show_calculation_info(frm);
		
		// Check account company match if both fields are filled
		if (frm.doc.amount_received_account && frm.doc.invested_company) {
			check_account_company_match(frm);
		}
		
		// Check for existing investor account
		if (frm.doc.investor_name && frm.doc.invested_company && frm.doc.docstatus === 0) {
			check_existing_account(frm);
		}
	},

	before_submit(frm) {
		if (!frm.doc.invested_amount || !frm.doc.exchange_rate || !frm.doc.amount_received_account) {
			frappe.throw(__('Please ensure all required fields are filled before submitting.'));
		}
	},

	// Safe calculation triggers with loop prevention
	invested_amount(frm) {
		if (!frm.calculating) {
			calculate_company_currency_amount(frm);
		}
	},

	exchange_rate(frm) {
		if (!frm.calculating) {
			calculate_company_currency_amount(frm);
		}
	},

	dividend(frm) {
		if (!frm.calculating) {
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
		}
	},

	invested_amount_company_currency(frm) {
		if (!frm.calculating) {
			calculate_dividend_amount(frm);
		}
	},

	// Currency change handler
	invested_currency(frm) {
		if (frm.doc.invested_currency && frm.doc.company_currency) {
			if (frm.doc.invested_currency === frm.doc.company_currency) {
				frm.set_value('exchange_rate', 1);
			} else {
				get_exchange_rate(frm);
			}
		}
	},

	// Field change handlers for validation
	investor_name(frm) {
		if (frm.doc.invested_company && frm.doc.docstatus === 0) {
			check_existing_account(frm);
		}
	},

	invested_project(frm) {
		if (frm.doc.investor_name && frm.doc.invested_company && frm.doc.docstatus === 0) {
			check_existing_account(frm);
		}
	},

	invested_company(frm) {
		// Update filters when company changes
		frm.trigger('setup');
		
		// Clear previous warnings
		frm.dashboard.clear_comment();
		
		// Get exchange rate if currencies are different
		if (frm.doc.invested_currency && frm.doc.company_currency && frm.doc.invested_currency !== frm.doc.company_currency) {
			get_exchange_rate(frm);
		}
	},

	amount_received_account(frm) {
		if (frm.doc.invested_company) {
			check_account_company_match(frm);
		}
	}
});

// SAFE CALCULATION FUNCTIONS WITH LOOP PREVENTION
function calculate_company_currency_amount(frm) {
	if (frm.doc.invested_amount && frm.doc.exchange_rate && !frm.calculating) {
		frm.calculating = true; // Prevent loops
		
		let invested_amount = flt(frm.doc.invested_amount);
		let exchange_rate = flt(frm.doc.exchange_rate);
		let converted_amount = flt(invested_amount * exchange_rate, 2);
		
		// Use direct assignment to avoid triggering events
		frm.doc.invested_amount_company_currency = converted_amount;
		frm.refresh_field('invested_amount_company_currency');
		
		// Calculate dividend amount automatically
		if (frm.doc.dividend) {
			calculate_dividend_amount(frm);
		}
		
		// Show conversion info in dashboard
		if (frm.doc.invested_currency && frm.doc.company_currency && frm.doc.invested_currency !== frm.doc.company_currency) {
			setTimeout(() => {
				show_calculation_info(frm);
			}, 100);
		}
		
		frm.calculating = false; // Release lock
	}
}

function calculate_dividend_amount(frm) {
	if (frm.doc.invested_amount_company_currency && frm.doc.dividend && !frm.calculating) {
		frm.calculating = true;
		
		let dividend_amount = flt(frm.doc.invested_amount_company_currency) * flt(frm.doc.dividend) / 100;
		
		// Use direct assignment to avoid triggering events
		frm.doc.eligable_dividend_amount_in_company_currency = dividend_amount;
		frm.refresh_field('eligable_dividend_amount_in_company_currency');
		
		frm.calculating = false;
	}
}

// EXCHANGE RATE FUNCTION
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
					frappe.show_alert({
						message: __('Exchange rate updated from ERPNext'),
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
				frm.set_value('exchange_rate', 1);
			}
		});
	}
}

// BUTTON MANAGEMENT
function add_custom_buttons(frm) {
	// Clear existing custom buttons
	frm.clear_custom_buttons();
	
	if (frm.doc.docstatus === 1) {
		// Submitted document buttons
		add_submitted_buttons(frm);
	} else if (frm.doc.docstatus === 0) {
		// Draft document buttons
		add_draft_buttons(frm);
	}
}

function add_submitted_buttons(frm) {
	// Create Journal Entry button
	if (!frm.doc.journal_entry) {
		frm.add_custom_button(__('Create Journal Entry'), function() {
			create_journal_entry_with_prefill(frm);
		}, __('Create'));
	}
	
	// View Journal Entry button
	if (frm.doc.journal_entry) {
		frm.add_custom_button(__('View Journal Entry'), function() {
			frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry);
		}, __('View'));
	}
}

function add_draft_buttons(frm) {
	// Preview Account Structure button
	if (frm.doc.investor_name && frm.doc.invested_company) {
		frm.add_custom_button(__('Preview Account'), function() {
			frappe.call({
				method: "preview_account_structure",
				doc: frm.doc,
				callback: function(r) {
					if (r.message) {
						show_preview_message(r.message);
					}
				}
			});
		}, __('Preview'));
	}
	
	// Fix Account Structure button
	if (frm.doc.invested_company) {
		frm.add_custom_button(__('Fix Account Structure'), function() {
			frappe.call({
				method: "fix_account_structure",
				doc: frm.doc,
				callback: function(r) {
					if (r.message) {
						show_fix_result(r.message);
						frm.reload_doc();
					}
				}
			});
		}, __('Tools'));
	}
	
	// Check Company Structure button
	if (frm.doc.invested_company) {
		frm.add_custom_button(__('Check Company'), function() {
			frappe.call({
				method: "gulf_energy.gulf_energy.doctype.investor.investor.get_company_structure_info",
				args: {
					company: frm.doc.invested_company
				},
				callback: function(r) {
					if (r.message) {
						show_company_structure_info(r.message);
					}
				}
			});
		}, __('Tools'));
	}
}

// VALIDATION FUNCTIONS
function check_existing_account(frm) {
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
					__('📋 Existing account found: <strong>{0}</strong> - Will be reused', [r.message.account_name]), 
					'orange', true
				);
			} else if (r.message && !r.message.exists) {
				frm.dashboard.add_comment(
					__('🆕 New account will be created: <strong>{0}</strong> in <strong>{1}</strong>', 
					[r.message.new_account_name, r.message.company]), 
					'blue', true
				);
			}
		}
	});
}

function check_account_company_match(frm) {
	frappe.call({
		method: "frappe.client.get_value",
		args: {
			doctype: "Account",
			name: frm.doc.amount_received_account,
			fieldname: ["company"]
		},
		callback: function(r) {
			if (r.message) {
				let account_company = r.message.company;
				
				if (account_company !== frm.doc.invested_company) {
					frm.dashboard.add_comment(
						__('⚠️ Warning: Bank account is in <strong>{0}</strong>, investment is for <strong>{1}</strong>', 
						[account_company, frm.doc.invested_company]), 
						'red', true
					);
				} else {
					frm.dashboard.add_comment(
						__('✅ Perfect: Bank account and investment both in <strong>{0}</strong>', [frm.doc.invested_company]), 
						'green', true
					);
				}
			}
		}
	});
}

// DISPLAY FUNCTIONS
function show_calculation_info(frm) {
	if (frm.doc.invested_amount && frm.doc.exchange_rate && frm.doc.invested_amount_company_currency) {
		if (frm.doc.invested_currency !== frm.doc.company_currency) {
			let message = __('💱 Conversion: {0} {1} × {2} = {3} {4}', [
				format_currency(frm.doc.invested_amount, frm.doc.invested_currency),
				frm.doc.invested_currency,
				frm.doc.exchange_rate,
				format_currency(frm.doc.invested_amount_company_currency, frm.doc.company_currency),
				frm.doc.company_currency
			]);
			
			frm.dashboard.add_comment(message, 'blue', true);
		}
		
		// Show dividend calculation
		if (frm.doc.dividend && frm.doc.eligable_dividend_amount_in_company_currency) {
			let dividend_message = __('💰 Dividend: {0} × {1}% = {2}', [
				format_currency(frm.doc.invested_amount_company_currency, frm.doc.company_currency),
				frm.doc.dividend,
				format_currency(frm.doc.eligable_dividend_amount_in_company_currency, frm.doc.company_currency)
			]);
			
			frm.dashboard.add_comment(dividend_message, 'green', true);
		}
	}
}

// JOURNAL ENTRY CREATION
function create_journal_entry_with_prefill(frm) {
	frappe.model.with_doctype("Journal Entry", function() {
		let je = frappe.model.get_new_doc("Journal Entry");
		
		// IMPORTANT: Use invested company and its currency
		je.company = frm.doc.invested_company;  // Use invested company for currency alignment
		je.posting_date = frm.doc.investe_date || frappe.datetime.get_today();
		je.user_remark = `Investment by ${frm.doc.investor_name} - ${frm.doc.name}`;
		
		// Use EXACT amount from field
		let exact_amount = frm.doc.invested_amount_company_currency;
		
		// Add bank account entry (DEBIT)
		let bank_row = frappe.model.add_child(je, "accounts");
		bank_row.account = frm.doc.amount_received_account;
		bank_row.debit_in_account_currency = exact_amount;
		bank_row.credit_in_account_currency = 0;
		bank_row.user_remark = `Cash from ${frm.doc.investor_name}`;
		bank_row.exchange_rate = 1;  // Single currency
		
		// Add investor account entry (CREDIT)
		let investor_row = frappe.model.add_child(je, "accounts");
		investor_row.account = frm.doc.investor_account;
		investor_row.debit_in_account_currency = 0;
		investor_row.credit_in_account_currency = exact_amount;
		investor_row.user_remark = `Investment by ${frm.doc.investor_name}`;
		investor_row.exchange_rate = 1;  // Single currency
		
		// Open the form
		frappe.set_route("Form", "Journal Entry", je.name);
		
		frappe.show_alert({
			message: __('JE created with amount: {0} {1}', [exact_amount, frm.doc.company_currency]),
			indicator: 'green'
		});
		
		setTimeout(() => {
			frappe.msgprint({
				title: __('Journal Entry Pre-filled'),
				message: `
					<div class="alert alert-success">
						<strong>✅ Pre-filled Successfully!</strong><br><br>
						<strong>Company:</strong> ${frm.doc.invested_company}<br>
						<strong>Currency:</strong> ${frm.doc.company_currency}<br>
						<strong>Amount:</strong> ${format_currency(exact_amount, frm.doc.company_currency)}<br><br>
						<strong>Accounts:</strong><br>
						• Debit: ${frm.doc.amount_received_account}<br>
						• Credit: ${frm.doc.investor_account}
					</div>
				`,
				indicator: 'green'
			});
		}, 1000);
	});
}

// MESSAGE DISPLAY FUNCTIONS
function show_preview_message(preview) {
	let message = '';
	
	if (preview.error) {
		message = `<div class="text-danger"><strong>Error:</strong> ${preview.error}</div>`;
	} else if (preview.action === 'reuse') {
		message = `
			<div class="alert alert-info">
				<strong>🔄 Account Reuse:</strong><br>
				${preview.message}<br>
				<small>No new account will be created.</small>
			</div>
		`;
	} else if (preview.action === 'create') {
		message = `
			<div class="alert alert-success">
				<strong>🆕 New Account Creation:</strong><br>
				<strong>Account Number:</strong> ${preview.account_number}<br>
				<strong>Account Name:</strong> ${preview.account_name}<br>
				<strong>Company:</strong> ${preview.company}<br>
				<small>${preview.message}</small>
			</div>
		`;
	}
	
	frappe.msgprint({
		title: __('Account Structure Preview'),
		message: message,
		indicator: preview.error ? 'red' : 'blue'
	});
}

function show_fix_result(result) {
	if (result.success) {
		frappe.msgprint({
			title: __('Account Structure Fixed'),
			message: `<div class="alert alert-success">
				<strong>✅ Success!</strong><br>
				${result.message}<br>
				<small>Account: ${result.account || 'Created successfully'}</small>
			</div>`,
			indicator: 'green'
		});
	} else {
		frappe.msgprint({
			title: __('Fix Failed'),
			message: `<div class="text-danger">
				<strong>❌ Error:</strong> ${result.error}<br>
				<small>Please check Chart of Accounts structure.</small>
			</div>`,
			indicator: 'red'
		});
	}
}

function show_company_structure_info(info) {
	let message = '';
	
	if (info.error) {
		message = `<div class="text-danger"><strong>Error:</strong> ${info.error}</div>`;
	} else {
		message = `
			<div class="alert alert-info">
				<strong>🏢 Company Structure:</strong><br>
				<strong>Company:</strong> ${info.company}<br>
				<strong>Has Investor Capital:</strong> ${info.has_investor_capital ? '✅ Yes' : '❌ No'}<br>
				<small>All accounts will be created in: ${info.company}</small>
			</div>
		`;
	}
	
	frappe.msgprint({
		title: __('Company Structure Info'),
		message: message,
		indicator: info.error ? 'red' : 'blue'
	});
}