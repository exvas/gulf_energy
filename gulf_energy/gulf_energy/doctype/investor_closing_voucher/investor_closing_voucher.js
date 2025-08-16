// Copyright (c) 2025, sammish and contributors
// For license information, please see license.txt

frappe.ui.form.on("Investor Closing Voucher", {
	refresh(frm) {
		// Set status based on docstatus
		if (frm.doc.docstatus === 0) {
			frm.set_value('status', 'Draft');
		} else if (frm.doc.docstatus === 1) {
			frm.set_value('status', 'Submitted');
		} else if (frm.doc.docstatus === 2) {
			frm.set_value('status', 'Cancelled');
		}
		
		// Set filters for project
		set_project_filter(frm);
		
		// Add custom buttons based on form state
		setup_custom_buttons(frm);
		
		// Add button to manually complete project if submitted
		if (frm.doc.docstatus === 1 && frm.doc.project) {
			frm.add_custom_button(__('Force Complete Project'), function() {
				force_complete_project(frm);
			}, __('Actions'));
		}
	},
	
	project(frm) {
		// Clear project name when project changes
		frm.set_value('project_name', '');
		
		// Fetch project name
		if (frm.doc.project) {
			frappe.db.get_value('Project', frm.doc.project, 'project_name', (r) => {
				if (r && r.project_name) {
					frm.set_value('project_name', r.project_name);
				}
			});
		}
		
		// Clear investors table when project changes
		frm.clear_table('investors');
		frm.refresh_field('investors');
		
		// Setup buttons when project changes
		setup_custom_buttons(frm);
	},
	
	company(frm) {
		// Clear project and investors when company changes
		frm.set_value('project', '');
		frm.set_value('project_name', '');
		frm.clear_table('investors');
		frm.refresh_field('investors');
		
		// Set project filter
		set_project_filter(frm);
		
		// Setup buttons when company changes
		setup_custom_buttons(frm);
	},

	posting_date(frm) {
		// Update dividend return date for all investors if changed
		if (frm.doc.posting_date && frm.doc.investors) {
			frm.doc.investors.forEach(function(investor) {
				if (!investor.dividend_return_date) {
					frappe.model.set_value(investor.doctype, investor.name, 'dividend_return_date', frm.doc.posting_date);
				}
			});
			frm.refresh_field('investors');
		}
	},

	dividend_return_date(frm) {
		// Update dividend return date for all investors
		if (frm.doc.dividend_return_date && frm.doc.investors) {
			frm.doc.investors.forEach(function(investor) {
				frappe.model.set_value(investor.doctype, investor.name, 'dividend_return_date', frm.doc.dividend_return_date);
			});
			frm.refresh_field('investors');
		}
	}
});

function set_project_filter(frm) {
	// Filter projects by company
	frm.set_query("project", function() {
		if (frm.doc.company) {
			return {
				filters: {
					company: frm.doc.company,
					status: "Open"
				}
			};
		}
	});
}

function fetch_project_investors(frm) {
	if (!frm.doc.project || !frm.doc.company) {
		frappe.msgprint(__('Please select Project and Company first'));
		return;
	}
	
	frappe.call({
		method: "gulf_energy.gulf_energy.doctype.investor_closing_voucher.investor_closing_voucher.get_project_investors",
		args: {
			project: frm.doc.project,
			company: frm.doc.company
		},
		callback: function(r) {
			if (r.message && r.message.length > 0) {
				// Clear existing investors
				frm.clear_table('investors');
				
				// Add fetched investors
				r.message.forEach(function(investor) {
					let row = frm.add_child('investors');
					row.investor_name = investor.investor_name;
					row.investor_id = investor.investor_id;
					row.investor_account = investor.investor_account;
					row.invested_amount = investor.invested_amount;
					row.dividend_percent = investor.dividend_percent;
					row.dividend_return_date = investor.dividend_return_date || frm.doc.dividend_return_date;
					row.eligible_dividend_amount = investor.eligible_dividend_amount;
					row.investor_record = investor.investor_record;
				});
				
				frm.refresh_field('investors');
				
				frappe.msgprint(__('Fetched {0} unprocessed investors for project {1}', [r.message.length, frm.doc.project]));
			} else {
				frappe.msgprint(__('No unprocessed investors found for the selected project. All investors may have already been processed.'));
			}
		},
		error: function(r) {
			frappe.msgprint(__('Failed to fetch investors. Please try again.'));
		}
	});
}

function show_summary_message(frm) {
	if (frm.doc.investors && frm.doc.investors.length > 0) {
		let total_dividend = 0;
		frm.doc.investors.forEach(function(investor) {
			total_dividend += flt(investor.eligible_dividend_amount);
		});
		
		let message = __('Ready to process dividend payments for {0} investors. Total dividend amount: {1}', 
			[frm.doc.investors.length, format_currency(total_dividend, frm.doc.currency)]);
		
		frm.dashboard.add_comment(message, 'blue', true);
	}
}

// Child table events
frappe.ui.form.on("Investor Closing Detail", {
	eligible_dividend_amount(frm, cdt, cdn) {
		calculate_totals(frm);
	},
	
	invested_amount(frm, cdt, cdn) {
		calculate_totals(frm);
	},
	
	investors_remove(frm) {
		calculate_totals(frm);
	}
});

function calculate_totals(frm) {
	let total_investment = 0;
	let total_dividend = 0;
	
	if (frm.doc.investors) {
		frm.doc.investors.forEach(function(investor) {
			total_investment += flt(investor.invested_amount);
			total_dividend += flt(investor.eligible_dividend_amount);
		});
	}

	frm.set_value('total_investment', total_investment);
	frm.set_value('total_dividend_amount', total_dividend);
	frm.set_value('total_investors', frm.doc.investors ? frm.doc.investors.length : 0);
}

function force_complete_project(frm) {
	// Validate that project field has a value
	if (!frm.doc.project) {
		frappe.msgprint(__('Please select a project first'));
		return;
	}

	frappe.confirm(
		__('Are you sure you want to manually mark project "{0}" as completed? This action cannot be undone.', [frm.doc.project]),
		function() {
			frappe.call({
				method: 'gulf_energy.gulf_energy.doctype.investor_closing_voucher.investor_closing_voucher.force_complete_project',
				args: {
					project: frm.doc.project
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						let message = r.message.message || __('Project marked as completed successfully');
						let indicator = r.message.already_completed ? 'orange' : 'green';
						
						frappe.show_alert({
							message: message,
							indicator: indicator
						});
						
						// Show detailed info if status changed
						if (!r.message.already_completed) {
							frappe.msgprint({
								title: __('Project Status Updated'),
								message: __('Project {0} status changed from "{1}" to "{2}"', 
									[frm.doc.project, r.message.old_status, r.message.new_status]),
								indicator: 'green'
							});
						}
						
						// Refresh form after a short delay
						setTimeout(() => {
							frm.reload_doc();
						}, 2000);
					}
				},
				error: function(r) {
					// The server method already throws proper error messages
					// This will be handled by the frappe error handling system
					console.error('Force complete project failed:', r);
				}
			});
		},
		function() {
			// User cancelled
			frappe.show_alert({
				message: __('Operation cancelled'),
				indicator: 'orange'
			});
		}
	);
}

function show_processing_history(frm) {
	if (!frm.doc.project || !frm.doc.company) {
		frappe.msgprint(__('Please select Project and Company first'));
		return;
	}
	
	frappe.call({
		method: "gulf_energy.gulf_energy.doctype.investor_closing_voucher.investor_closing_voucher.get_investor_processing_history",
		args: {
			project: frm.doc.project,
			company: frm.doc.company
		},
		callback: function(r) {
			if (r.message && r.message.length > 0) {
				let history_html = '<div class="processing-history">';
				history_html += '<h4>Processing History for Project ' + frm.doc.project + '</h4>';
				
				r.message.forEach(function(record) {
					history_html += '<div class="voucher-record" style="margin-bottom: 15px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">';
					history_html += '<strong>Voucher:</strong> ' + record.voucher + ' | ';
					history_html += '<strong>Date:</strong> ' + record.posting_date + ' | ';
					history_html += '<strong>Investors:</strong> ' + record.total_investors + ' | ';
					history_html += '<strong>Total Dividend:</strong> ' + format_currency(record.total_dividend) + '<br>';
					
					if (record.investors && record.investors.length > 0) {
						history_html += '<strong>Processed Investors:</strong><br>';
						record.investors.forEach(function(inv) {
							history_html += '• ' + inv.investor_name + ' (' + inv.investor_id + ') - ' + 
								format_currency(inv.eligible_dividend_amount) + '<br>';
						});
					}
					
					history_html += '</div>';
				});
				
				history_html += '</div>';
				
				frappe.msgprint({
					title: __('Investor Processing History'),
					message: history_html,
					indicator: 'blue'
				});
			} else {
				frappe.msgprint(__('No processing history found for this project'));
			}
		}
	});
}

function setup_custom_buttons(frm) {
	// Clear existing custom buttons
	frm.clear_custom_buttons();
	
	// Add fetch investors button for draft documents with project and company
	if (frm.doc.project && frm.doc.company && frm.doc.docstatus === 0) {
		frm.add_custom_button(__('Fetch Project Investors'), function() {
			fetch_project_investors(frm);
		});
	}
	
	// Add view processing history button if project exists
	if (frm.doc.project && frm.doc.company) {
		frm.add_custom_button(__('View Processing History'), function() {
			show_processing_history(frm);
		});
	}
	
	// Add force complete project button for submitted documents
	if (frm.doc.docstatus === 1 && frm.doc.project) {
		frm.add_custom_button(__('Force Complete Project'), function() {
			force_complete_project(frm);
		}, __('Actions'));
	}
}
