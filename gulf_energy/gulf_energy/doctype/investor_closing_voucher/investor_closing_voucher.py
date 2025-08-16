# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, today


class InvestorClosingVoucher(Document):
	def validate(self):
		self.validate_required_fields()
		self.set_dividend_expense_account()
		self.calculate_totals()
	
	def validate_required_fields(self):
		"""Validate required fields"""
		if not self.project:
			frappe.throw(_("Project is required"))
		
		if not self.company:
			frappe.throw(_("Company is required"))
		
		if not self.dividend_return_date:
			frappe.throw(_("Dividend Return Date is required"))
		
		if not self.investors:
			frappe.throw(_("At least one investor must be selected"))
		
		# Check for duplicate investor IDs within the same voucher
		investor_ids = []
		for investor in self.investors:
			if investor.investor_id in investor_ids:
				frappe.throw(_("Duplicate Investor ID {0} found in the voucher. Each investor can only be processed once per voucher.").format(investor.investor_id))
			investor_ids.append(investor.investor_id)
	
	def set_dividend_expense_account(self):
		"""Set dividend expense account from Global Settings"""
		if self.company:
			# Get dividend expense account from Global Settings
			global_settings = frappe.get_single("Global Settings")
			if global_settings and global_settings.investor_dividend_expense:
				# Validate account belongs to the company
				account_company = frappe.get_value("Account", global_settings.investor_dividend_expense, "company")
				if account_company == self.company:
					self.dividend_expense_account = global_settings.investor_dividend_expense
				else:
					frappe.throw(_("Dividend Expense Account in Global Settings does not belong to company {0}").format(self.company))
			else:
				frappe.throw(_("Please set Investor Dividend Expense Account in Global Settings"))
	
	def calculate_totals(self):
		"""Calculate total investment, dividend amount, and investor count"""
		total_investment = 0
		total_dividend = 0
		
		for investor in self.investors:
			if investor.invested_amount:
				total_investment += flt(investor.invested_amount)
			if investor.eligible_dividend_amount:
				total_dividend += flt(investor.eligible_dividend_amount)
		
		self.total_investment = total_investment
		self.total_dividend_amount = total_dividend
		self.total_investors = len(self.investors)
	
	def on_submit(self):
		"""Create journal entries for dividend payments and update project status"""
		self.create_dividend_journal_entries()
		self.update_project_status("Completed")
		self.status = "Submitted"
		self.db_set("status", "Submitted")
	
	def on_cancel(self):
		"""Cancel related journal entries and revert project status"""
		self.cancel_journal_entries()
		self.update_project_status("Open")
		self.status = "Cancelled"
		self.db_set("status", "Cancelled")
	
	def create_dividend_journal_entries(self):
		"""Create journal entries for dividend payments"""
		if not self.investors:
			frappe.throw(_("No investors found to process"))
		
		try:
			for investor in self.investors:
				if investor.eligible_dividend_amount and investor.eligible_dividend_amount > 0:
					# Create journal entry for each investor
					journal_entry = self.create_investor_journal_entry(investor)
					
					# Add to journal entries table
					self.append("journal_entries", {
						"journal_entry": journal_entry.name,
						"investor_name": investor.investor_name,
						"dividend_amount": investor.eligible_dividend_amount,
						"status": "Submitted"
					})
			
			frappe.msgprint(_("Created {0} journal entries for dividend payments").format(len(self.journal_entries)))
			
		except Exception as e:
			frappe.throw(_("Failed to create journal entries: {0}").format(str(e)))
	
	def create_investor_journal_entry(self, investor):
		"""Create journal entry for individual investor dividend payment"""
		if not investor.eligible_dividend_amount or investor.eligible_dividend_amount <= 0:
			frappe.throw(_("Invalid dividend amount for investor {0}").format(investor.investor_name))
		
		# Prepare journal entry accounts
		accounts = [
			{
				"account": self.dividend_expense_account,
				"debit_in_account_currency": investor.eligible_dividend_amount,
				"debit": investor.eligible_dividend_amount,
				"project": self.project
			},
			{
				"account": investor.investor_account,
				"credit_in_account_currency": investor.eligible_dividend_amount,
				"credit": investor.eligible_dividend_amount,
				"project": self.project
			}
		]
		
		# Prepare user remark
		user_remark = f"Dividend Payment to {investor.investor_name} - {self.name}"
		if self.project:
			project_name = frappe.get_value("Project", self.project, "project_name") or self.project
			user_remark += f" (Project: {project_name})"
		
		# Create journal entry
		journal_entry = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"company": self.company,
			"posting_date": self.posting_date,
			"user_remark": user_remark,
			"project": self.project,
			"accounts": accounts,
			"reference_type": "Investor Closing Voucher",
			"reference_name": self.name
		})
		
		journal_entry.insert(ignore_permissions=True)
		journal_entry.submit()
		
		return journal_entry
	
	def cancel_journal_entries(self):
		"""Cancel all related journal entries"""
		for je in self.journal_entries:
			if je.journal_entry:
				try:
					journal_entry = frappe.get_doc("Journal Entry", je.journal_entry)
					if journal_entry.docstatus == 1:
						journal_entry.cancel()
						# Update status using db_set to avoid update after submit error
						frappe.db.set_value("Investor Closing Journal Entry", je.name, "status", "Cancelled")
				except Exception as e:
					frappe.log_error(f"Failed to cancel journal entry {je.journal_entry}: {str(e)}")
		
		frappe.msgprint(_("Cancelled related journal entries"))
	
	def update_project_status(self, status):
		"""Update project status"""
		if not self.project:
			return
		
		try:
			# Get the project document
			project = frappe.get_doc("Project", self.project)
			
			# Special handling for completion status
			if status == "Completed":
				# Check if there are any pending investors for this project
				pending_investors = get_project_investors(self.project, self.company)
				
				# Only mark as completed if no pending investors or this is a forced completion
				if len(pending_investors) == 0:
					if project.status != status:
						project.status = status
						project.save(ignore_permissions=True)
						
						frappe.msgprint(_("Project {0} marked as Completed - all investors have been processed").format(self.project))
						
						comment_text = f"Project completed - all investors processed via Investor Closing Voucher {self.name}"
						project.add_comment("Info", comment_text)
				else:
					# Don't change status if there are still pending investors
					frappe.msgprint(_("Project {0} has {1} unprocessed investors remaining").format(self.project, len(pending_investors)), indicator="orange")
			
			elif status == "Open":
				# Revert to Open status on cancellation
				if project.status != status:
					project.status = status
					project.save(ignore_permissions=True)
					
					frappe.msgprint(_("Project {0} status reverted to Open").format(self.project))
					
					comment_text = f"Project status reverted to Open due to cancellation of Investor Closing Voucher {self.name}"
					project.add_comment("Info", comment_text)
				
		except Exception as e:
			frappe.log_error(f"Failed to update project status: {str(e)}", "Project Status Update Error")
			# Don't throw error as this shouldn't block the main process


@frappe.whitelist()
def get_project_investors(project, company):
	"""Get all investors for a specific project (excluding already processed ones)"""
	if not project or not company:
		return []
	
	# Get already processed investors from submitted Investor Closing Vouchers
	processed_investors = frappe.get_all("Investor Closing Detail", 
		filters={
			"parenttype": "Investor Closing Voucher",
			"parent": ["in", frappe.get_all("Investor Closing Voucher", 
				filters={"docstatus": 1, "project": project, "company": company}, 
				pluck="name")]
		},
		fields=["investor_record"]
	)
	
	# Get list of already processed investor record IDs
	processed_investor_ids = [inv.investor_record for inv in processed_investors if inv.investor_record]
	
	# Prepare filter conditions
	filters = {
		"invested_project": project,
		"invested_company": company,
		"docstatus": 1  # Only submitted records
	}
	
	# Exclude already processed investors
	if processed_investor_ids:
		filters["name"] = ["not in", processed_investor_ids]
	
	# Get all submitted investor records for the project (excluding processed ones)
	investors = frappe.get_all("Investor", 
		filters=filters,
		fields=[
			"name", "investor_name", "investor_account", 
			"invested_amount_company_currency", "dividend",
			"dividend_return_date", "eligable_dividend_amount_in_company_currency",
			"company_currency"
		]
	)
	
	investor_list = []
	for inv in investors:
		investor_list.append({
			"investor_name": inv.investor_name,
			"investor_id": inv.name,  # This is the Investor ID
			"investor_account": inv.investor_account,
			"invested_amount": inv.invested_amount_company_currency,
			"dividend_percent": inv.dividend,
			"dividend_return_date": inv.dividend_return_date,
			"eligible_dividend_amount": inv.eligable_dividend_amount_in_company_currency,
			"investor_record": inv.name
		})
	
	return investor_list


@frappe.whitelist()
def get_project_name(project):
	"""Get project name"""
	if not project:
		return ""
	
	return frappe.get_value("Project", project, "project_name") or project


@frappe.whitelist()
def get_investor_processing_history(project, company):
	"""Get history of processed investors for a project"""
	if not project or not company:
		return []
	
	# Get all submitted Investor Closing Vouchers for this project
	vouchers = frappe.get_all("Investor Closing Voucher",
		filters={
			"project": project,
			"company": company,
			"docstatus": 1
		},
		fields=["name", "posting_date", "total_investors", "total_dividend_amount"]
	)
	
	history = []
	for voucher in vouchers:
		# Get investors processed in this voucher
		investors = frappe.get_all("Investor Closing Detail",
			filters={
				"parent": voucher.name,
				"parenttype": "Investor Closing Voucher"
			},
			fields=["investor_name", "investor_id", "eligible_dividend_amount"]
		)
		
		history.append({
			"voucher": voucher.name,
			"posting_date": voucher.posting_date,
			"total_investors": voucher.total_investors,
			"total_dividend": voucher.total_dividend_amount,
			"investors": investors
		})
	
	return history


@frappe.whitelist()
def force_complete_project(project):
	"""Manually mark project as completed regardless of remaining investors"""
	try:
		# Check if project exists
		if not frappe.db.exists('Project', project):
			# Get all existing projects for reference
			existing_projects = frappe.get_all('Project', fields=['name', 'project_name'], limit=10)
			error_msg = _("Project '{0}' not found.").format(project)
			if existing_projects:
				project_list = ", ".join([f"{p.name} ({p.project_name})" for p in existing_projects])
				error_msg += _(" Available projects: {0}").format(project_list)
			frappe.throw(error_msg)
		
		# Get the project document to check current status
		project_doc = frappe.get_doc('Project', project)
		old_status = project_doc.status or 'Unknown'
		
		# Check if already completed
		if project_doc.status == 'Completed':
			return {
				'success': True,
				'message': _("Project {0} is already completed").format(project),
				'already_completed': True
			}
		
		# Update project status to Completed
		project_doc.status = 'Completed'
		project_doc.save(ignore_permissions=True)
		
		# Add comment to project for audit trail
		comment_text = _('Project manually marked as completed via Investor Closing Voucher by {0}. Previous status: {1}').format(frappe.session.user, old_status)
		project_doc.add_comment('Info', comment_text)
		
		frappe.db.commit()
		
		frappe.msgprint(_("Project {0} has been successfully marked as completed").format(project), indicator='green')
		return {
			'success': True,
			'message': _("Project {0} status updated from {1} to Completed").format(project, old_status),
			'old_status': old_status,
			'new_status': 'Completed'
		}
		
	except Exception as e:
		error_msg = _("Error completing project {0}: {1}").format(project, str(e))
		frappe.log_error(f"Failed to force complete project {project}: {str(e)}", "Force Complete Project Error")
		frappe.throw(error_msg)
