# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, today


class Investor(Document):
	def validate(self):
		self.validate_required_fields()
		self.calculate_company_currency_amount()
		self.calculate_dividend_amount()
		self.validate_accounts()
		
	def validate_required_fields(self):
		"""Validate required fields"""
		if not self.invested_amount or self.invested_amount <= 0:
			frappe.throw(_("Invested Amount must be greater than zero"))
		
		if not self.exchange_rate or self.exchange_rate <= 0:
			frappe.throw(_("Exchange Rate must be greater than zero"))
		
		# Validate dividend percentage if provided
		if self.dividend is not None and self.dividend < 0:
			frappe.throw(_("Dividend percentage cannot be negative"))
		
		if self.dividend and self.dividend > 100:
			frappe.throw(_("Dividend percentage cannot exceed 100%"))
	
	def validate_accounts(self):
		"""Validate account selections"""
		if self.amount_received_account:
			account_company = frappe.get_value("Account", self.amount_received_account, "company")
			if account_company != self.invested_company:
				frappe.throw(_("Amount Received Account must belong to the selected company"))
		
		if self.investor_account:
			account_company = frappe.get_value("Account", self.investor_account, "company")
			if account_company != self.invested_company:
				frappe.throw(_("Investor Account must belong to the selected company"))
		
		if self.invested_project:
			project_company = frappe.get_value("Project", self.invested_project, "company")
			if project_company != self.invested_company:
				frappe.throw(_("Selected project must belong to the selected company"))
		
	def calculate_company_currency_amount(self):
		"""Calculate invested amount in company currency"""
		if self.invested_amount and self.exchange_rate:
			self.invested_amount_company_currency = flt(self.invested_amount) * flt(self.exchange_rate)
	
	def calculate_dividend_amount(self):
		"""Calculate eligible dividend amount in company currency"""
		if self.invested_amount_company_currency and self.dividend:
			dividend_rate = flt(self.dividend) / 100
			self.eligable_dividend_amount_in_company_currency = flt(self.invested_amount_company_currency) * dividend_rate
	
	def validate_company_account_structure(self):
		"""Validate and ensure company has proper investor account structure"""
		if not self.invested_company:
			frappe.throw(_("Invested Company is required"))
		
		frappe.msgprint(_("🔍 Validating account structure for company: {0}").format(self.invested_company))
		
		# Check if Investor Capital exists for the invested company
		investor_capital = frappe.db.get_value("Account", {
			"account_name": "Investor Capital",
			"company": self.invested_company,
			"is_group": 1
		}, "name")
		
		if not investor_capital:
			frappe.msgprint(_("⚠️ No Investor Capital account found for {0}. Will create during account creation.").format(self.invested_company), indicator="orange")
		else:
			frappe.msgprint(_("✅ Account structure validation passed for {0}").format(self.invested_company), indicator="green")
	
	def on_submit(self):
		"""Create investor account on submit - DON'T FAIL if JE fails"""
		try:
			# Step 1: Validate and create accounts (REQUIRED)
			self.validate_company_account_structure()
			self.create_investor_account()
			
			frappe.msgprint(_("✅ Investor account created successfully: {0}").format(self.investor_account), indicator="green")
			
			# Step 2: Try journal entry creation (OPTIONAL - don't fail submission)
			try:
				frappe.msgprint(_("🔄 Attempting to create journal entry automatically..."), indicator="blue")
				
				# Try to create journal entry but don't let it fail the submission
				je_result = self.create_automated_journal_entry()
				
				if je_result and je_result.get("auto_created"):
					frappe.msgprint(_("✅ Journal entry created automatically: {0}").format(je_result.get("je_name")), indicator="green")
				else:
					frappe.msgprint(_("⚠️ Auto-creation failed. Manual creation will be available."), indicator="orange")
					
			except Exception as je_error:
				# Log the JE error but don't fail submission
				frappe.log_error(f"JE auto-creation failed: {str(je_error)}", "JE Auto Creation")
				frappe.msgprint(_("⚠️ Auto-creation failed. Manual creation will be available."), indicator="orange")
			
			# Submission should ALWAYS succeed if we reach here
			frappe.msgprint(_("📝 Submission completed successfully. Journal entry can be created manually if needed."), indicator="blue")
			
		except Exception as e:
			# Only fail submission for critical errors (account creation, etc.)
			frappe.log_error(f"Critical submission error: {str(e)}", "Investor Submission Error")
			frappe.throw(_("Submission failed: {0}").format(str(e)))

	@frappe.whitelist()
	def create_automated_journal_entry(self):
		"""Create journal entry - SAFE VERSION that doesn't cause submission failures"""
		if self.docstatus != 1:
			return {"success": False, "error": "Document must be submitted first"}
		
		if self.journal_entry:
			return {"success": False, "error": f"Journal entry already exists: {self.journal_entry}"}
		
		amount = flt(self.invested_amount_company_currency, 2)
		posting_date = getattr(self, 'investe_date', None) or today()
		
		try:
			# Use a simpler approach - create JE without complex transaction handling
			je_data = {
				"doctype": "Journal Entry",
				"company": self.invested_company,
				"posting_date": posting_date,
				"user_remark": f"Investment by {self.investor_name} - {self.name}",
				"accounts": [
					{
						"account": self.amount_received_account,
						"debit_in_account_currency": amount,
						"credit_in_account_currency": 0,
						"user_remark": f"Cash from {self.investor_name}"
					},
					{
						"account": self.investor_account,
						"debit_in_account_currency": 0,
						"credit_in_account_currency": amount,
						"user_remark": f"Investment by {self.investor_name}"
					}
				]
			}
			
			# Create journal entry
			je = frappe.get_doc(je_data)
			je.flags.ignore_permissions = True
			je.insert()
			
			# Link to investor record
			self.db_set("journal_entry", je.name, update_modified=False)
			frappe.db.commit()
			
			# Try to submit (if this fails, JE will be in draft for manual submission)
			try:
				je.submit()
				return {
					"success": True,
					"auto_created": True,
					"je_name": je.name,
					"message": f"Journal Entry {je.name} created and submitted automatically"
				}
			except Exception as submit_error:
				# JE created but not submitted - user can submit manually
				return {
					"success": True,
					"auto_created": False,
					"je_name": je.name,
					"message": f"Journal Entry {je.name} created but not submitted. Please submit manually.",
					"submit_error": str(submit_error)
				}
				
		except Exception as e:
			# Complete failure - return manual creation data
			return {
				"success": False,
				"auto_created": False,
				"error": str(e),
				"manual_data": {
					"company": self.invested_company,
					"posting_date": posting_date,
					"amount": amount,
					"bank_account": self.amount_received_account,
					"investor_account": self.investor_account,
					"user_remark": f"Investment by {self.investor_name} - {self.name}"
				}
			}
	
	def create_investor_account(self):
		"""Create a new account or reuse existing account for same investor-project combination"""
		if self.investor_account:
			return  # Account already exists
		
		# Check if account already exists for this investor-project combination
		existing_account = self.find_existing_investor_account()
		if existing_account:
			self.db_set("investor_account", existing_account)
			frappe.msgprint(_("Using existing investor account: {0}").format(existing_account))
			return
			
		# Get the parent account
		parent_account = frappe.get_value("Account", 
			{"account_name": "Investor Capital", "company": self.invested_company}, 
			"name")
		
		if not parent_account:
			# Try to find by account number
			parent_account = frappe.get_value("Account", 
				{"account_number": "3110", "company": self.invested_company}, 
				"name")
		
		if not parent_account:
			frappe.throw(_("Investor Capital account (3110) not found for company {0}. Please create it first.").format(self.invested_company))
		
		try:
			# Generate unique account name and number
			account_name = self.generate_unique_account_name()
			account_number = self.generate_unique_account_number()
			
			# Create new account
			account_doc = frappe.get_doc({
				"doctype": "Account",
				"account_name": account_name,  # Investor-Project combination
				"account_number": account_number,  # I30XX format
				"parent_account": parent_account,
				"company": self.invested_company,
				"account_type": "Equity",
				"root_type": "Equity",
				"is_group": 0,
				"account_currency": self.company_currency
			})
			
			account_doc.insert(ignore_permissions=True)
			
			# Update investor document with the new account
			self.db_set("investor_account", account_doc.name)
			
			frappe.msgprint(_("Created investor account: {0} | Account Number: {1}").format(account_doc.name, account_number))
		
		except Exception as e:
			frappe.throw(_("Failed to create investor account: {0}").format(str(e)))
	
	def find_existing_investor_account(self):
		"""Find existing investor account for same investor-project combination"""
		if not self.investor_name:
			return None
		
		# Build search criteria based on investor name and project
		if self.invested_project:
			# Look for account with investor name and project combination
			account_name_pattern = f"{self.investor_name}-{self.invested_project}"
		else:
			# Look for account with just investor name (no project)
			account_name_pattern = self.investor_name
		
		# Search for existing account
		existing_account = frappe.get_value("Account", {
			"account_name": account_name_pattern,
			"company": self.invested_company,
			"parent_account": ["like", "%Investor Capital%"]
		}, "name")
		
		return existing_account
	
	def generate_unique_account_number(self):
		"""Generate next available I30XX account number"""
		# Get existing investor accounts with I30XX pattern
		existing_accounts = frappe.get_all("Account",
			filters={
				"company": self.invested_company,
				"parent_account": ["like", "%Investor Capital%"],
				"account_number": ["like", "I30%"]
			},
			fields=["account_number"],
			order_by="account_number"
		)
		
		# Extract numbers from existing account numbers
		used_numbers = set()
		for account in existing_accounts:
			if account.account_number and account.account_number.startswith("I30"):
				try:
					number = int(account.account_number[3:])  # Extract number after "I30"
					if 1 <= number <= 999:  # Valid range I3001 to I3999
						used_numbers.add(number)
				except ValueError:
					continue
		
		# Find the next available number starting from 1
		for i in range(1, 1000):  # I3001 to I3999
			if i not in used_numbers:
				return f"I30{i:02d}"  # Format as I3001, I3002, etc.
		
		# If somehow all numbers are used (very unlikely), throw error
		frappe.throw(_("All investor account numbers (I3001-I3999) are exhausted"))
	
	def generate_unique_account_name(self):
		"""Generate unique account name with investor-project combination"""
		# Build account name with project if available
		if self.invested_project:
			account_name = f"{self.investor_name}-{self.invested_project}"
		else:
			account_name = self.investor_name
		
		return account_name
	
	def create_journal_entry(self):
		"""Create journal entry for the investment"""
		if not self.investor_account or not self.amount_received_account:
			frappe.throw(_("Both Investor Account and Amount Received Account are required"))
		
		try:
			# Prepare journal entry accounts
			accounts = [
				{
					"account": self.amount_received_account,
					"debit_in_account_currency": self.invested_amount_company_currency,
					"debit": self.invested_amount_company_currency
				},
				{
					"account": self.investor_account,
					"credit_in_account_currency": self.invested_amount_company_currency,
					"credit": self.invested_amount_company_currency
				}
			]
			
			# Add project to accounts if invested_project is specified
			if self.invested_project:
				for account in accounts:
					account["project"] = self.invested_project
			
			# Prepare user remark with project information if available
			user_remark = f"Investment by {self.investor_name} - {self.name}"
			if self.invested_project:
				user_remark += f" (Project: {self.project_name or self.invested_project})"
			
			journal_entry = frappe.get_doc({
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.invested_company,
				"posting_date": self.investe_date or today(),
				"user_remark": user_remark,
				"accounts": accounts
			})
			
			# Add project to journal entry header if specified
			if self.invested_project:
				journal_entry.project = self.invested_project
			
			journal_entry.insert(ignore_permissions=True)
			journal_entry.submit()
			
			frappe.msgprint(_("Created and submitted journal entry: {0}").format(journal_entry.name))
			
			# Link the journal entry to the investor record
			self.db_set("journal_entry", journal_entry.name)
			
		except Exception as e:
			frappe.throw(_("Failed to create journal entry: {0}").format(str(e)))
	
	def on_cancel(self):
		"""Cancel related journal entry when investor is cancelled"""
		if self.journal_entry:
			journal_entry = frappe.get_doc("Journal Entry", self.journal_entry)
			if journal_entry.docstatus == 1:
				journal_entry.cancel()
				frappe.msgprint(_("Cancelled journal entry: {0}").format(journal_entry.name))


@frappe.whitelist()
def check_existing_investor_account(investor_name, invested_company, invested_project=None):
	"""Check if investor account already exists for investor-project combination"""
	if not investor_name or not invested_company:
		return {"exists": False, "account_name": None}
	
	# Build search criteria based on investor name and project
	if invested_project:
		account_name_pattern = f"{investor_name}-{invested_project}"
	else:
		account_name_pattern = investor_name
	
	# Search for existing account
	existing_account = frappe.get_value("Account", {
		"account_name": account_name_pattern,
		"company": invested_company,
		"parent_account": ["like", "%Investor Capital%"]
	}, ["name", "account_number"])
	
	if existing_account:
		return {
			"exists": True,
			"account_name": f"{existing_account[0]} | Account Number: {existing_account[1]}"
		}
	else:
		return {
			"exists": False,
			"new_account_name": account_name_pattern
		}


@frappe.whitelist()
def preview_investor_account_name(investor_name, invested_company, invested_project=None):
	"""Preview what the investor account name will be"""
	# Check if account already exists
	result = check_existing_investor_account(investor_name, invested_company, invested_project)
	
	if result["exists"]:
		return f"Existing Account: {result['account_name']}"
	else:
		# Generate what the new account would look like
		if invested_project:
			account_name = f"{investor_name}-{invested_project}"
		else:
			account_name = investor_name
		
		# Get next available account number
		existing_accounts = frappe.get_all("Account",
			filters={
				"company": invested_company,
				"parent_account": ["like", "%Investor Capital%"],
				"account_number": ["like", "I30%"]
			},
			fields=["account_number"],
			order_by="account_number"
		)
		
		used_numbers = set()
		for account in existing_accounts:
			if account.account_number and account.account_number.startswith("I30"):
				try:
					number = int(account.account_number[3:])
					if 1 <= number <= 999:
						used_numbers.add(number)
				except ValueError:
					continue
		
		# Find next available number
		for i in range(1, 1000):
			if i not in used_numbers:
				account_number = f"I30{i:02d}"
				return f"New Account: {account_name} | Account Number: {account_number}"
		
		return f"New Account: {account_name} | Account Number: [Number Generation Error]"
