# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, today
import time


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
		"""Simple account validation - accounts should be in invested company"""
		# Validate Amount Received Account
		if self.amount_received_account:
			try:
				account_details = frappe.get_value("Account", self.amount_received_account, 
					["company", "account_type", "is_group"], as_dict=True)
				if not account_details:
					frappe.throw(_("Amount Received Account does not exist"))
				
				# Check if account is in the invested company
				if account_details.company != self.invested_company:
					frappe.msgprint(_("⚠️ Warning: Bank account belongs to {0}, but investment is for {1}. Please select a bank account from {1}.").format(
						account_details.company, self.invested_company), indicator="orange")
				
			except Exception:
				frappe.throw(_("Invalid Amount Received Account"))
		
		# Skip investor account validation during creation
		if self.investor_account and not self.is_new():
			try:
				account_company = frappe.get_value("Account", self.investor_account, "company")
				if account_company and account_company != self.invested_company:
					frappe.throw(_("Investor Account must belong to the invested company ({0})").format(self.invested_company))
			except Exception:
				pass
		
		# Validate project if selected
		if self.invested_project and self.invested_company:
			try:
				project_company = frappe.get_value("Project", self.invested_project, "company")
				if project_company and project_company != self.invested_company:
					frappe.throw(_("Selected project must belong to the selected company"))
			except Exception:
				frappe.throw(_("Invalid project selection"))
	
	def before_save(self):
		"""Clean setup before save"""
		pass
		
	def calculate_company_currency_amount(self):
		"""Calculate invested amount in company currency"""
		if self.invested_amount and self.exchange_rate:
			invested_amount = flt(self.invested_amount)
			exchange_rate = flt(self.exchange_rate)
			converted_amount = flt(invested_amount * exchange_rate, 2)
			self.invested_amount_company_currency = converted_amount
	
	def calculate_dividend_amount(self):
		"""Calculate eligible dividend amount in company currency"""
		if self.invested_amount_company_currency and self.dividend:
			dividend_rate = flt(self.dividend) / 100
			self.eligable_dividend_amount_in_company_currency = flt(self.invested_amount_company_currency) * dividend_rate
	
	def on_submit(self):
		"""Create investor account on submit - SIMPLIFIED"""
		self.validate_company_account_structure()
		self.create_investor_account()
		self.create_journal_entry()
	
	def create_investor_account(self):
		"""Create investor account in the INVESTED company - SIMPLIFIED"""
		if not self.investor_name:
			frappe.throw(_("Investor Name is required to create an account"))
		
		if not self.invested_company:
			frappe.throw(_("Invested Company is required to create an account"))
		
		# SIMPLE: Use the INVESTED company directly
		target_company = self.invested_company
		
		frappe.msgprint(_("Creating investor account for {0} in company {1}").format(
			self.investor_name, target_company))
		
		# Check if account already exists in INVESTED company
		existing_account = self.find_existing_investor_account()
		if existing_account:
			self.db_set("investor_account", existing_account)
			frappe.msgprint(_("Using existing investor account: {0}").format(existing_account))
			return existing_account
		
		# Find parent account in INVESTED company
		parent_account = frappe.db.get_value("Account", 
			{
				"account_name": "Investor Capital", 
				"company": target_company,  # Use invested company
				"is_group": 1
			}, 
			"name")
		
		if not parent_account:
			# Create the Investor Capital account in INVESTED company
			parent_account = self.create_investor_capital_account_if_missing(target_company)
		
		try:
			# Generate unique account name and number
			account_name = self.generate_unique_account_name()
			account_number = self.generate_unique_account_number(target_company)
			
			# Get INVESTED company's default currency
			company_currency = frappe.get_cached_value("Company", target_company, "default_currency")
			
			frappe.msgprint(_("Creating account: {0} | Number: {1} | Company: {2}").format(
				account_name, account_number, target_company))
			
			# Create new account in INVESTED COMPANY
			account_doc = frappe.get_doc({
				"doctype": "Account",
				"account_name": account_name,
				"account_number": account_number,
				"parent_account": parent_account,
				"company": target_company,  # CREATE IN INVESTED COMPANY
				"account_type": "Equity",
				"root_type": "Equity",
				"is_group": 0,
				"account_currency": company_currency
			})
			
			account_doc.insert(ignore_permissions=True)
			
			# Update investor document with the new account
			self.db_set("investor_account", account_doc.name)
			
			frappe.msgprint(_("✅ Successfully created investor account: {0} in {1}").format(
				account_doc.name, target_company))
				
			return account_doc.name
		
		except Exception as e:
			error_msg = _("Failed to create investor account in {0}: {1}").format(target_company, str(e))
			frappe.log_error(error_msg, "Investor Account Creation")
			frappe.throw(error_msg)

	def find_existing_investor_account(self):
		"""Find existing investor account for same investor-project combination in invested company"""
		if not self.investor_name:
			return None
		
		# Build search criteria based on investor name and project
		if self.invested_project:
			account_name_pattern = f"{self.investor_name}-{self.invested_project}"
		else:
			account_name_pattern = self.investor_name
		
		# Search for existing account in INVESTED company
		existing_account = frappe.get_value("Account", {
			"account_name": account_name_pattern,
			"company": self.invested_company,  # Search in invested company
			"parent_account": ["like", "%Investor Capital%"]
		}, "name")
		
		return existing_account
	
	def create_investor_capital_account_if_missing(self, company):
		"""Create Investor Capital account in INVESTED company"""
		frappe.msgprint(_("Creating Investor Capital account in: {0}").format(company))
		
		# Check if already exists
		investor_capital = frappe.db.get_value("Account", {
			"account_name": "Investor Capital",
			"company": company,
			"is_group": 1
		}, "name")
		
		if investor_capital:
			return investor_capital
		
		# Find equity parent in INVESTED company
		equity_parent = frappe.db.get_value("Account", {
			"company": company,
			"root_type": "Equity",
			"is_group": 1,
			"parent_account": ["in", ["", None]]
		}, "name")
		
		if not equity_parent:
			equity_accounts = frappe.get_all("Account", {
				"company": company,
				"root_type": "Equity",
				"is_group": 1
			}, ["name"], limit=1)
			
			if equity_accounts:
				equity_parent = equity_accounts[0].name
			else:
				frappe.throw(_("No equity account found in {0}").format(company))
		
		try:
			company_currency = frappe.get_cached_value("Company", company, "default_currency")
			
			# Check if account number 3110 is available
			existing_3110 = frappe.db.get_value("Account", {
				"account_number": "3110",
				"company": company
			}, "name")
			
			account_number = "3111" if existing_3110 else "3110"
			
			# Create Investor Capital group account
			investor_capital_doc = frappe.get_doc({
				"doctype": "Account",
				"account_name": "Investor Capital",
				"account_number": account_number,
				"parent_account": equity_parent,
				"company": company,
				"account_type": "Equity",
				"root_type": "Equity",
				"is_group": 1,
				"account_currency": company_currency
			})
			
			investor_capital_doc.insert(ignore_permissions=True)
			
			frappe.msgprint(_("✅ Created Investor Capital account: {0}").format(investor_capital_doc.name))
			return investor_capital_doc.name
			
		except Exception as e:
			frappe.throw(_("Failed to create Investor Capital account in {0}: {1}").format(company, str(e)))

	def generate_unique_account_number(self, company):
		"""Generate next available I30XX account number in specific company"""
		# Get existing investor accounts with I30XX pattern from company
		existing_accounts = frappe.get_all("Account",
			filters={
				"company": company,
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
					number = int(account.account_number[3:])
					if 1 <= number <= 999:
						used_numbers.add(number)
				except ValueError:
					continue
		
		# Find the next available number starting from 1
		for i in range(1, 1000):
			if i not in used_numbers:
				return f"I30{i:02d}"
		
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
		"""Create journal entry in INVESTED company - SIMPLIFIED"""
		if not self.investor_account or not self.amount_received_account:
			frappe.throw(_("Both Investor Account and Amount Received Account are required"))
		
		if not self.invested_amount_company_currency:
			frappe.throw(_("Invested Amount in Company Currency is required"))
		
		amount = flt(self.invested_amount_company_currency, 2)
		posting_date = getattr(self, 'investe_date', None) or today()
		
		# SIMPLE: Create JE in INVESTED company
		target_company = self.invested_company
		
		frappe.msgprint(_("Creating journal entry in: {0}").format(target_company))
		
		# Get company currency and fix account currencies
		company_currency = frappe.get_cached_value("Company", target_company, "default_currency")
		
		# Ensure account currencies match
		frappe.db.set_value("Account", self.amount_received_account, "account_currency", company_currency)
		frappe.db.set_value("Account", self.investor_account, "account_currency", company_currency)
		frappe.db.commit()
		
		try:
			journal_entry = frappe.get_doc({
				"doctype": "Journal Entry",
				"company": target_company,  # Use invested company
				"posting_date": posting_date,
				"user_remark": f"Investment by {self.investor_name} - {self.name}",
				"multi_currency": 0,
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
			})
			
			journal_entry.insert(ignore_permissions=True)
			journal_entry.submit()
			
			self.db_set("journal_entry", journal_entry.name)
			frappe.msgprint(_("✅ Journal entry created: {0}").format(journal_entry.name))
			
			return journal_entry.name
			
		except Exception as e:
			frappe.log_error(f"Simple JE failed: {str(e)}", "Simple JE Error")
			frappe.throw(_("Failed to create journal entry: {0}").format(str(e)))

	@frappe.whitelist()
	def create_manual_journal_entry(self):
		"""Create journal entry manually after submission"""
		if self.docstatus != 1:
			frappe.throw(_("Document must be submitted before creating journal entry"))
		
		if self.journal_entry:
			frappe.throw(_("Journal entry already exists: {0}").format(self.journal_entry))
		
		try:
			je_name = self.create_journal_entry()
			return {
				"success": True,
				"je_name": je_name,
				"auto_created": True,
				"message": f"Journal entry created successfully: {je_name}"
			}
		except Exception as e:
			return {
				"success": False,
				"error": str(e),
				"message": f"Failed to create journal entry: {str(e)}"
			}
	
	def on_cancel(self):
		"""Cancel the related journal entry when investor is cancelled"""
		if self.journal_entry:
			try:
				journal_entry = frappe.get_doc("Journal Entry", self.journal_entry)
				if journal_entry.docstatus == 1:  # If submitted
					journal_entry.cancel()
					frappe.msgprint(_("Related journal entry {0} has been cancelled").format(self.journal_entry))
			except Exception as e:
				frappe.log_error(f"Failed to cancel journal entry {self.journal_entry}: {str(e)}", "Investor Cancellation")
				frappe.msgprint(_("Warning: Could not cancel related journal entry {0}. Please cancel it manually.").format(self.journal_entry))
	
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

	@frappe.whitelist()
	def preview_account_structure(self):
		"""Preview what account will be created for this investor"""
		if not self.invested_company:
			return {"error": "Please select Invested Company first"}
		
		if not self.investor_name:
			return {"error": "Please enter Investor Name first"}
		
		try:
			# Check if account already exists
			existing_account = self.find_existing_investor_account()
			if existing_account:
				account_info = frappe.get_value("Account", existing_account, "account_number")
				return {
					"action": "reuse",
					"account_name": f"{existing_account} | Account Number: {account_info}",
					"company": self.invested_company,
					"message": f"Will reuse existing account: {existing_account}"
				}
			
			# Preview new account creation
			account_name = self.generate_unique_account_name()
			account_number = self.generate_unique_account_number(self.invested_company)
			
			# Check parent account status
			parent_account = frappe.db.get_value("Account", {
				"account_name": "Investor Capital",
				"company": self.invested_company,
				"is_group": 1
			}, "name")
			
			parent_status = "exists" if parent_account else "will be created"
			
			return {
				"action": "create",
				"account_name": account_name,
				"account_number": account_number,
				"company": self.invested_company,
				"parent_account": parent_account or "3110 - Investor Capital",
				"parent_status": parent_status,
				"message": f"Will create new account: {account_number} - {account_name} in {self.invested_company}"
			}
			
		except Exception as e:
			return {"error": str(e)}
	
	@frappe.whitelist()
	def fix_account_structure(self):
		"""Fix account structure for the invested company"""
		if not self.invested_company:
			return {"error": "Invested Company is required"}
		
		try:
			# Check if Investor Capital already exists
			existing_investor_capital = frappe.db.get_value("Account", {
				"account_name": "Investor Capital",
				"company": self.invested_company,
				"is_group": 1
			}, "name")
			
			if existing_investor_capital:
				return {
					"success": True,
					"message": f"Investor Capital account already exists for {self.invested_company}",
					"account": existing_investor_capital
				}
			
			# Create new Investor Capital account
			result_account = self.create_investor_capital_account_if_missing(self.invested_company)
			
			return {
				"success": True,
				"message": f"Successfully created Investor Capital account for {self.invested_company}",
				"account": result_account
			}
			
		except Exception as e:
			return {
				"success": False,
				"error": str(e)
			}


# UTILITY FUNCTIONS
@frappe.whitelist()
def check_existing_investor_account(investor_name, invested_company, invested_project=None):
	"""Check if investor account already exists"""
	try:
		# Build search criteria
		if invested_project:
			account_name_pattern = f"{investor_name}-{invested_project}"
		else:
			account_name_pattern = investor_name
		
		# Search for existing account in invested company
		existing_account = frappe.get_value("Account", {
			"account_name": account_name_pattern,
			"company": invested_company,
			"parent_account": ["like", "%Investor Capital%"]
		}, "name")
		
		if existing_account:
			return {
				"exists": True,
				"account_name": existing_account,
				"company": invested_company
			}
		else:
			return {
				"exists": False,
				"new_account_name": account_name_pattern,
				"company": invested_company
			}
			
	except Exception as e:
		return {"error": str(e)}

@frappe.whitelist()
def get_company_structure_info(company):
	"""Get company structure info"""
	if not company:
		return {"error": "Company is required"}
	
	if not frappe.db.exists("Company", company):
		return {"error": f"Company {company} does not exist"}
	
	try:
		# Check if Investor Capital exists
		has_investor_capital = bool(frappe.db.get_value("Account", {
			"account_name": "Investor Capital",
			"company": company,
			"is_group": 1
		}, "name"))
		
		return {
			"company": company,
			"has_investor_capital": has_investor_capital
		}
		
	except Exception as e:
		return {"error": str(e)}
