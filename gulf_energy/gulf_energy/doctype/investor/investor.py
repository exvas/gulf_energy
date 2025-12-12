# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, today


def get_root_company(company):
	"""Dynamic function to find the root company"""
	try:
		if not company:
			return None
			
		company_details = frappe.get_cached_value("Company", company, ["is_group", "parent_company"])
		if not company_details:
			return company
			
		is_group = company_details[0] if len(company_details) > 0 else 0
		parent_company = company_details[1] if len(company_details) > 1 else None
		
		# Root company criteria
		if is_group or not parent_company:
			frappe.msgprint(_("🏢 Root Company: {0}").format(company), indicator="blue")
			return company
		
		# Traverse up the parent chain
		current_company = parent_company
		traversal_path = [company]
		
		while current_company:
			traversal_path.append(current_company)
			
			parent_details = frappe.get_cached_value("Company", current_company, ["is_group", "parent_company"])
			if not parent_details:
				break
				
			current_is_group = parent_details[0] if len(parent_details) > 0 else 0
			current_parent = parent_details[1] if len(parent_details) > 1 else None
			
			if current_is_group or not current_parent:
				frappe.msgprint(_("🏢 Root Company Found: {0}").format(current_company), indicator="green")
				return current_company
			
			current_company = current_parent
			
			if len(traversal_path) > 10:  # Safety check
				break
		
		root = traversal_path[-1] if traversal_path else company
		return root
		
	except Exception as e:
		frappe.log_error(f"Error finding root company for {company}: {str(e)}", "Root Company Error")
		return company


def journal_entry_has_custom_investor_field():
	"""Check if Journal Entry doctype has custom_investor field"""
	try:
		# Check if custom field exists
		custom_field_exists = frappe.db.exists("Custom Field", {
			"dt": "Journal Entry",
			"fieldname": "custom_investor"
		})
		
		if custom_field_exists:
			return True
		
		# Also check if field exists in the doctype schema
		# This is a more robust check but requires the doctype to be loaded
		from frappe.model.meta import get_meta
		meta = get_meta("Journal Entry")
		return "custom_investor" in meta.get_fieldnames()
		
	except Exception:
		# If any error occurs, assume field doesn't exist
		return False


@frappe.whitelist()
def check_existing_investor_account(investor_name, invested_company, invested_project=None):
	"""
	Check if an investor account already exists for the given investor/company/project combination.
	Called from client-side to show user whether account will be reused or created.
	"""
	if not investor_name or not invested_company:
		return {"exists": False, "message": "Missing required parameters"}

	# Get root company
	root_company = get_root_company(invested_company)

	# Get company abbreviation
	company_abbr = frappe.get_cached_value("Company", invested_company, "abbr")
	if not company_abbr:
		company_abbr = invested_company[:3].upper()

	# Build account name pattern
	if invested_project:
		account_name_pattern = f"{investor_name}-{invested_project}-{company_abbr}"
	else:
		account_name_pattern = f"{investor_name}-{company_abbr}"

	# Check if account exists
	existing_account = frappe.db.get_value("Account", {
		"account_name": account_name_pattern,
		"company": root_company,
		"parent_account": ["like", "%Investor Capital%"]
	}, "name")

	if existing_account:
		return {
			"exists": True,
			"account_name": existing_account,
			"company": root_company
		}
	else:
		return {
			"exists": False,
			"new_account_name": account_name_pattern,
			"company": root_company
		}


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
				
				root_company = get_root_company(self.invested_company)
				
				if account_details.company != self.invested_company and account_details.company != root_company:
					frappe.msgprint(_("⚠️ Cross-Company: Bank in {0}, will handle via smart logic").format(
						account_details.company), indicator="orange")
				
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
		"""ENHANCED: Auto-create JE during submission"""
		try:
			# Step 1: Create investor account
			self.validate_company_account_structure()
			self.create_investor_account()
			frappe.msgprint(_("✅ Investor account created: {0}").format(self.investor_account), indicator="green")
			
			# Step 2: AUTO-CREATE Journal Entry (ALWAYS)
			frappe.msgprint(_("🔄 Auto-creating journal entry..."), indicator="blue")
			
			je_name = self.create_automated_journal_entry()
			
			if je_name:
				frappe.msgprint(_("✅ Journal entry auto-created: {0}").format(je_name), indicator="green")
				frappe.msgprint(_("🎉 Investment process completed successfully!"), indicator="green")
			else:
				# If auto-creation fails, still complete submission but show warning
				frappe.msgprint(_("⚠️ Auto JE failed. Submission completed. Create JE manually."), indicator="orange")
			
		except Exception as e:
			# Only fail if critical error (not JE creation)
			if "journal" not in str(e).lower():
				frappe.throw(_("Submission failed: {0}").format(str(e)))
			else:
				frappe.msgprint(_("✅ Submission completed. JE creation failed: {0}").format(str(e)), indicator="orange")
	
	def create_investor_account(self):
		"""ENHANCED: Create account with company abbreviation"""
		if not self.investor_name or not self.invested_company:
			frappe.throw(_("Investor Name and Company required"))
		
		# Get root company
		root_company = get_root_company(self.invested_company)
		
		frappe.msgprint(_("🎯 Investment: {0} → Root: {1}").format(
			self.invested_company, root_company), indicator="blue")
		
		# Check for existing account
		existing_account = self.find_existing_investor_account(root_company)
		if existing_account:
			self.db_set("investor_account", existing_account)
			frappe.msgprint(_("♻️ Using existing: {0}").format(existing_account), indicator="green")
			return existing_account
		
		# Find or create parent account
		parent_account = frappe.db.get_value("Account", 
			{"account_name": "Investor Capital", "company": root_company, "is_group": 1}, "name")
		
		if not parent_account:
			frappe.msgprint(_("🔧 Creating Investor Capital in: {0}").format(root_company), indicator="orange")
			parent_account = self.create_investor_capital_account_if_missing(root_company)
		
		# Generate account details WITH ABBREVIATION
		account_name = self.generate_unique_account_name_with_abbr()
		account_number = self.generate_unique_account_number(root_company)
		company_currency = frappe.get_cached_value("Company", root_company, "default_currency")
		
		frappe.msgprint(_("🆕 Creating: {0} - {1}").format(account_number, account_name), indicator="blue")
		
		# Create account in ROOT COMPANY
		account_doc = frappe.get_doc({
			"doctype": "Account",
			"account_name": account_name,
			"account_number": account_number,
			"parent_account": parent_account,
			"company": root_company,
			"account_type": "Equity",
			"root_type": "Equity",
			"is_group": 0,
			"account_currency": company_currency,
			"remarks": f"Investor account for {self.invested_company} investment"
		})
		
		account_doc.insert(ignore_permissions=True)
		self.db_set("investor_account", account_doc.name)
		
		frappe.msgprint(_("✅ Created: {0}").format(account_doc.name), indicator="green")
		return account_doc.name

	def generate_unique_account_name_with_abbr(self):
		"""ENHANCED: Generate account name with company abbreviation"""
		# Get invested company abbreviation
		company_abbr = frappe.get_cached_value("Company", self.invested_company, "abbr")
		if not company_abbr:
			company_abbr = self.invested_company[:3].upper()  # Fallback to first 3 characters
		
		# Build account name: InvestorName-Project-CompanyAbbr
		if self.invested_project:
			account_name = f"{self.investor_name}-{self.invested_project}-{company_abbr}"
		else:
			account_name = f"{self.investor_name}-{company_abbr}"
		
		frappe.msgprint(_("📝 Account pattern: {0}").format(account_name), indicator="blue")
		return account_name

	def find_existing_investor_account(self, root_company):
		"""Find existing account with abbreviation pattern"""
		if not self.investor_name:
			return None
		
		# Get company abbreviation for search
		company_abbr = frappe.get_cached_value("Company", self.invested_company, "abbr")
		if not company_abbr:
			company_abbr = self.invested_company[:3].upper()
		
		# Build search pattern
		if self.invested_project:
			account_name_pattern = f"{self.investor_name}-{self.invested_project}-{company_abbr}"
		else:
			account_name_pattern = f"{self.investor_name}-{company_abbr}"
		
		return frappe.get_value("Account", {
			"account_name": account_name_pattern,
			"company": root_company,
			"parent_account": ["like", "%Investor Capital%"]
		}, "name")

	def create_automated_journal_entry(self):
		"""FIXED: Use Company Currency and auto-create during submission"""
		if not self.investor_account or not self.amount_received_account:
			frappe.throw(_("Both accounts required for JE creation"))
		
		# Use the EXACT amount from the field
		if not self.invested_amount_company_currency:
			frappe.throw(_("Invested Amount Company Currency is required"))
		
		amount = flt(self.invested_amount_company_currency, 2)
		posting_date = getattr(self, 'investe_date', None) or today()
		
		# CRITICAL FIX: Get the company currency from invested company
		target_company_currency = frappe.get_cached_value("Company", self.invested_company, "default_currency")
		
		frappe.msgprint(_("💰 Amount: {0}, Company Currency: {1}").format(amount, target_company_currency), indicator="blue")
		
		# Determine JE company strategy
		je_company, strategy = self.determine_je_company()
		
		frappe.msgprint(_("📋 Strategy: {0} in {1}").format(strategy, je_company), indicator="blue")
		
		try:
			# Always use company currency for the JE
			je_company_currency = frappe.get_cached_value("Company", je_company, "default_currency")
			
			# CRITICAL: If JE company currency differs from invested company, convert or use invested company
			if je_company_currency != target_company_currency:
				frappe.msgprint(_("⚠️ Currency mismatch: JE company uses {0}, but amount is in {1}").format(
					je_company_currency, target_company_currency), indicator="orange")
				
				# Use invested company instead for currency consistency
				je_company = self.invested_company
				je_company_currency = target_company_currency
				strategy = "CURRENCY_ALIGNED"
				
				frappe.msgprint(_("🔄 Switched to invested company for currency alignment: {0}").format(je_company), indicator="blue")
			
			# Create JE with proper currency
			return self.create_je_with_correct_currency(je_company, amount, posting_date, je_company_currency, strategy)
			
		except Exception as e:
			frappe.log_error(f"Auto JE creation failed: {str(e)}", "Auto JE Error")
			frappe.msgprint(_("⚠️ Auto JE failed. Check error log."), indicator="red")
			return None

	def create_je_with_correct_currency(self, company, amount, posting_date, company_currency, strategy):
		"""Create JE with correct currency handling"""
		
		# Ensure accounts exist in the target company or find equivalents
		bank_account = self.amount_received_account
		investor_account = self.investor_account
		
		# Check if accounts belong to the JE company
		bank_account_company = frappe.get_value("Account", bank_account, "company")
		investor_account_company = frappe.get_value("Account", investor_account, "company")
		
		# Handle cross-company accounts
		if bank_account_company != company:
			# Find equivalent bank account in JE company
			equivalent_bank = self.find_equivalent_bank_account(company)
			if equivalent_bank:
				bank_account = equivalent_bank
				frappe.msgprint(_("🔄 Using equivalent bank: {0}").format(bank_account), indicator="blue")
			else:
				frappe.throw(_("No suitable bank account found in company {0}").format(company))
		
		if investor_account_company != company:
			# Find or create equivalent investor account in JE company
			equivalent_investor = self.find_or_create_equivalent_investor_account(company)
			if equivalent_investor:
				investor_account = equivalent_investor
				frappe.msgprint(_("🔄 Using equivalent investor: {0}").format(investor_account), indicator="blue")
			else:
				frappe.throw(_("No suitable investor account found in company {0}").format(company))
		
		# Ensure account currencies match company currency
		self.ensure_account_currencies_match(bank_account, investor_account, company_currency)
		
		frappe.msgprint(_("💰 Creating JE: Amount {0} {1} in company {2}").format(
			amount, company_currency, company), indicator="green")
		
		# Create the journal entry
		je_dict = {
			"doctype": "Journal Entry",
			"company": company,
			"posting_date": posting_date,
			"user_remark": f"Auto-Investment by {self.investor_name} - {self.name}",
			"multi_currency": 0,  # Single currency
			"accounts": [
				{
					"account": bank_account,
					"debit_in_account_currency": amount,
					"credit_in_account_currency": 0,
					"debit": amount,  # Base currency amount
					"credit": 0,
					"user_remark": f"Cash from {self.investor_name}",
					"exchange_rate": 1,  # Single currency
					"project": self.invested_project  # Add project to account line
				},
				{
					"account": investor_account,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": amount,
					"debit": 0,
					"credit": amount,  # Base currency amount
					"user_remark": f"Investment by {self.investor_name}",
					"exchange_rate": 1,  # Single currency
					"project": self.invested_project  # Add project to account line
				}
			]
		}
		
		# Set project if available
		if self.invested_project:
			je_dict["project"] = self.invested_project
			frappe.msgprint(_("📋 Project set in JE: {0}").format(self.invested_project), indicator="blue")
		
		# Try to set custom_investor if the field exists in the doctype
		has_custom_investor_field = journal_entry_has_custom_investor_field()

		if has_custom_investor_field:
			je_dict["custom_investor"] = self.name
			frappe.msgprint(_("📋 Custom Investor set in JE: {0}").format(self.name), indicator="blue")

		je_doc = frappe.get_doc(je_dict)
		je_doc.insert(ignore_permissions=True)
		je_doc.submit()

		# Link JE to Investor
		self.db_set("journal_entry", je_doc.name)

		return je_doc.name

	def determine_je_company(self):
		"""Determine which company to create the JE in"""
		bank_account_company = frappe.get_value("Account", self.amount_received_account, "company")

		if bank_account_company == self.invested_company:
			return self.invested_company, "SAME_COMPANY"

		# Check if bank is in root company
		root_company = get_root_company(self.invested_company)
		if bank_account_company == root_company:
			return root_company, "ROOT_COMPANY"

		# Default to invested company
		return self.invested_company, "INVESTED_COMPANY"

	def find_equivalent_bank_account(self, company):
		"""Find an equivalent bank/cash account in the specified company"""
		# Try to find a similar account type
		original_account = frappe.get_doc("Account", self.amount_received_account)

		equivalent = frappe.db.get_value("Account", {
			"company": company,
			"account_type": original_account.account_type,
			"is_group": 0
		}, "name")

		if equivalent:
			return equivalent

		# Fallback: find any cash account
		cash_account = frappe.db.get_value("Account", {
			"company": company,
			"account_type": "Cash",
			"is_group": 0
		}, "name")

		return cash_account

	def find_or_create_equivalent_investor_account(self, company):
		"""Find or create an equivalent investor account in the specified company"""
		# Check if account already exists in target company
		existing = frappe.db.get_value("Account", {
			"account_name": ["like", f"%{self.investor_name}%"],
			"company": company,
			"parent_account": ["like", "%Investor Capital%"]
		}, "name")

		if existing:
			return existing

		# Create new account in target company
		parent_account = frappe.db.get_value("Account", {
			"account_name": "Investor Capital",
			"company": company,
			"is_group": 1
		}, "name")

		if not parent_account:
			parent_account = self.create_investor_capital_account_if_missing(company)

		company_currency = frappe.get_cached_value("Company", company, "default_currency")
		company_abbr = frappe.get_cached_value("Company", company, "abbr") or company[:3].upper()

		account_name = f"{self.investor_name}-{self.invested_project}-{company_abbr}" if self.invested_project else f"{self.investor_name}-{company_abbr}"
		account_number = self.generate_unique_account_number(company)

		account_doc = frappe.get_doc({
			"doctype": "Account",
			"account_name": account_name,
			"account_number": account_number,
			"parent_account": parent_account,
			"company": company,
			"account_type": "Equity",
			"root_type": "Equity",
			"is_group": 0,
			"account_currency": company_currency
		})

		account_doc.insert(ignore_permissions=True)
		return account_doc.name

	def ensure_account_currencies_match(self, bank_account, investor_account, company_currency):
		"""Ensure account currencies match company currency"""
		bank_currency = frappe.get_value("Account", bank_account, "account_currency")
		investor_currency = frappe.get_value("Account", investor_account, "account_currency")

		if bank_currency and bank_currency != company_currency:
			frappe.msgprint(_("⚠️ Bank account currency ({0}) differs from company currency ({1})").format(
				bank_currency, company_currency), indicator="orange")

		if investor_currency and investor_currency != company_currency:
			frappe.msgprint(_("⚠️ Investor account currency ({0}) differs from company currency ({1})").format(
				investor_currency, company_currency), indicator="orange")

	def validate_company_account_structure(self):
		"""Validate that the company has proper account structure"""
		root_company = get_root_company(self.invested_company)

		# Check if Investor Capital account exists
		investor_capital = frappe.db.get_value("Account", {
			"account_name": "Investor Capital",
			"company": root_company,
			"is_group": 1
		}, "name")

		if not investor_capital:
			frappe.msgprint(_("Creating Investor Capital account structure for {0}").format(root_company), indicator="blue")
			self.create_investor_capital_account_if_missing(root_company)

	def create_investor_capital_account_if_missing(self, company):
		"""Create Investor Capital parent account if missing"""
		existing = frappe.db.get_value("Account", {
			"account_name": "Investor Capital",
			"company": company,
			"is_group": 1
		}, "name")

		if existing:
			return existing

		# Find parent equity account
		equity_accounts = frappe.get_all("Account", {
			"company": company,
			"root_type": "Equity",
			"is_group": 1
		}, ["name", "account_name"], order_by="lft")

		if not equity_accounts:
			frappe.throw(_("No equity accounts found for company {0}").format(company))

		parent_equity = equity_accounts[0].name
		company_currency = frappe.get_cached_value("Company", company, "default_currency")

		investor_capital_doc = frappe.get_doc({
			"doctype": "Account",
			"account_name": "Investor Capital",
			"account_number": "3110",
			"parent_account": parent_equity,
			"company": company,
			"account_type": "Equity",
			"root_type": "Equity",
			"is_group": 1,
			"account_currency": company_currency
		})

		investor_capital_doc.insert(ignore_permissions=True)
		frappe.msgprint(_("✅ Created Investor Capital account: {0}").format(investor_capital_doc.name), indicator="green")

		return investor_capital_doc.name

	def generate_unique_account_number(self, company):
		"""Generate a unique account number for investor accounts"""
		# Get max account number starting with I3 in the company
		max_number = frappe.db.sql("""
			SELECT MAX(CAST(SUBSTRING(account_number, 2) AS UNSIGNED))
			FROM `tabAccount`
			WHERE company = %s
			AND account_number LIKE 'I3%%'
		""", company)

		if max_number and max_number[0][0]:
			next_number = int(max_number[0][0]) + 1
		else:
			next_number = 3001

		return f"I{next_number}"
	