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
		if not self.invested_amount or self.invested_amount <= 0:
			frappe.throw(_("Invested Amount must be greater than zero"))
		if not self.exchange_rate or self.exchange_rate <= 0:
			frappe.throw(_("Exchange Rate must be greater than zero"))
		if self.dividend is not None and self.dividend < 0:
			frappe.throw(_("Dividend percentage cannot be negative"))
		if self.dividend and self.dividend > 100:
			frappe.throw(_("Dividend percentage cannot exceed 100%"))
	
	def validate_accounts(self):
		if self.amount_received_account:
			try:
				account_details = frappe.get_value("Account", self.amount_received_account, 
					["company", "account_type"], as_dict=True)
				if not account_details:
					frappe.throw(_("Amount Received Account does not exist"))
				if account_details.company != self.invested_company:
					frappe.msgprint(_("⚠️ Warning: Bank account belongs to {0}, investment is for {1}").format(
						account_details.company, self.invested_company), indicator="orange")
			except Exception:
				frappe.throw(_("Invalid Amount Received Account"))
	
	def calculate_company_currency_amount(self):
		if self.invested_amount and self.exchange_rate:
			invested_amount = flt(self.invested_amount)
			exchange_rate = flt(self.exchange_rate)
			converted_amount = flt(invested_amount * exchange_rate, 2)
			self.invested_amount_company_currency = converted_amount
	
	def calculate_dividend_amount(self):
		if self.invested_amount_company_currency and self.dividend:
			dividend_rate = flt(self.dividend) / 100
			self.eligable_dividend_amount_in_company_currency = flt(self.invested_amount_company_currency) * dividend_rate
	
	def on_submit(self):
		try:
			self.validate_company_account_structure()
			self.create_investor_account()
			frappe.msgprint(_("✅ Investor account created: {0}").format(self.investor_account), indicator="green")
			frappe.msgprint(_("📝 Please create journal entry manually using the button."), indicator="blue")
		except Exception as e:
			frappe.throw(_("Submission failed: {0}").format(str(e)))
	
	def create_investor_account(self):
		if not self.investor_name or not self.invested_company:
			frappe.throw(_("Investor Name and Company required"))
		
		existing_account = self.find_existing_investor_account()
		if existing_account:
			self.db_set("investor_account", existing_account)
			return existing_account
		
		parent_account = frappe.db.get_value("Account", 
			{"account_name": "Investor Capital", "company": self.invested_company, "is_group": 1}, "name")
		
		if not parent_account:
			parent_account = self.create_investor_capital_account_if_missing(self.invested_company)
		
		account_name = self.generate_unique_account_name()
		account_number = self.generate_unique_account_number(self.invested_company)
		company_currency = frappe.get_cached_value("Company", self.invested_company, "default_currency")
		
		account_doc = frappe.get_doc({
			"doctype": "Account",
			"account_name": account_name,
			"account_number": account_number,
			"parent_account": parent_account,
			"company": self.invested_company,
			"account_type": "Equity",
			"root_type": "Equity",
			"is_group": 0,
			"account_currency": company_currency
		})
		
		account_doc.insert(ignore_permissions=True)
		self.db_set("investor_account", account_doc.name)
		return account_doc.name

	def find_existing_investor_account(self):
		if not self.investor_name:
			return None
		
		account_name_pattern = f"{self.investor_name}-{self.invested_project}" if self.invested_project else self.investor_name
		
		return frappe.get_value("Account", {
			"account_name": account_name_pattern,
			"company": self.invested_company,
			"parent_account": ["like", "%Investor Capital%"]
		}, "name")
	
	def create_investor_capital_account_if_missing(self, company):
		existing = frappe.db.get_value("Account", {
			"account_name": "Investor Capital", "company": company, "is_group": 1}, "name")
		if existing:
			return existing
		
		equity_parent = frappe.db.get_value("Account", {
			"company": company, "root_type": "Equity", "is_group": 1, 
			"parent_account": ["in", ["", None]]}, "name")
		
		if not equity_parent:
			equity_accounts = frappe.get_all("Account", {
				"company": company, "root_type": "Equity", "is_group": 1}, ["name"], limit=1)
			if equity_accounts:
				equity_parent = equity_accounts[0].name
			else:
				frappe.throw(_("No equity account found"))
		
		company_currency = frappe.get_cached_value("Company", company, "default_currency")
		existing_3110 = frappe.db.get_value("Account", {"account_number": "3110", "company": company}, "name")
		account_number = "3111" if existing_3110 else "3110"
		
		account_doc = frappe.get_doc({
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
		
		account_doc.insert(ignore_permissions=True)
		return account_doc.name

	def generate_unique_account_number(self, company):
		existing_accounts = frappe.get_all("Account", {
			"company": company,
			"parent_account": ["like", "%Investor Capital%"],
			"account_number": ["like", "I30%"]
		}, ["account_number"])
		
		used_numbers = set()
		for account in existing_accounts:
			if account.account_number and account.account_number.startswith("I30"):
				try:
					number = int(account.account_number[3:])
					if 1 <= number <= 999:
						used_numbers.add(number)
				except ValueError:
					continue
		
		for i in range(1, 1000):
			if i not in used_numbers:
				return f"I30{i:02d}"
		
		frappe.throw(_("All investor account numbers exhausted"))
	
	def generate_unique_account_name(self):
		return f"{self.investor_name}-{self.invested_project}" if self.invested_project else self.investor_name

	def validate_company_account_structure(self):
		if not self.invested_company:
			frappe.throw(_("Invested Company is required"))

	@frappe.whitelist()
	def create_manual_journal_entry(self):
		if self.docstatus != 1:
			frappe.throw(_("Document must be submitted"))
		if self.journal_entry:
			frappe.throw(_("Journal entry already exists"))
		
		return {
			"success": True,
			"message": "Create journal entry manually",
			"data": {
				"company": self.invested_company,
				"amount": self.invested_amount_company_currency,
				"bank_account": self.amount_received_account,
				"investor_account": self.investor_account
			}
		}

	@frappe.whitelist()
	def preview_account_structure(self):
		if not self.invested_company or not self.investor_name:
			return {"error": "Company and Investor Name required"}
		
		existing = self.find_existing_investor_account()
		if existing:
			return {"action": "reuse", "account_name": existing, "message": f"Will reuse: {existing}"}
		
		account_name = self.generate_unique_account_name()
		account_number = self.generate_unique_account_number(self.invested_company)
		
		return {
			"action": "create",
			"account_name": account_name,
			"account_number": account_number,
			"company": self.invested_company,
			"message": f"Will create: {account_number} - {account_name}"
		}

	@frappe.whitelist()
	def fix_account_structure(self):
		if not self.invested_company:
			return {"error": "Company required"}
		
		try:
			existing = frappe.db.get_value("Account", {
				"account_name": "Investor Capital", "company": self.invested_company, "is_group": 1}, "name")
			
			if existing:
				return {"success": True, "message": "Already exists", "account": existing}
			
			result = self.create_investor_capital_account_if_missing(self.invested_company)
			return {"success": True, "message": "Created successfully", "account": result}
		except Exception as e:
			return {"success": False, "error": str(e)}

# UTILITY FUNCTIONS
@frappe.whitelist()
def check_existing_investor_account(investor_name, invested_company, invested_project=None):
	try:
		account_name_pattern = f"{investor_name}-{invested_project}" if invested_project else investor_name
		
		existing = frappe.get_value("Account", {
			"account_name": account_name_pattern,
			"company": invested_company,
			"parent_account": ["like", "%Investor Capital%"]
		}, "name")
		
		if existing:
			return {"exists": True, "account_name": existing, "company": invested_company}
		else:
			return {"exists": False, "new_account_name": account_name_pattern, "company": invested_company}
	except Exception as e:
		return {"error": str(e)}

@frappe.whitelist()
def get_company_structure_info(company):
	if not company or not frappe.db.exists("Company", company):
		return {"error": "Invalid company"}
	
	try:
		has_investor_capital = bool(frappe.db.get_value("Account", {
			"account_name": "Investor Capital", "company": company, "is_group": 1}, "name"))
		return {"company": company, "has_investor_capital": has_investor_capital}
	except Exception as e:
		return {"error": str(e)}
