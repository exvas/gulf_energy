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
		je_doc = frappe.get_doc({
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
					"exchange_rate": 1  # Single currency
				},
				{
					"account": investor_account,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": amount,
					"debit": 0,
					"credit": amount,  # Base currency amount
					"user_remark": f"Investment by {self.investor_name}",
					"exchange_rate": 1  # Single currency
				}
			]
		})
		
		# Set totals explicitly
		je_doc.total_debit = amount
		je_doc.total_credit = amount
		je_doc.difference = 0
		
		# Insert and submit
		je_doc.flags.ignore_permissions = True
		je_doc.insert()
		
		# Link to investor record
		self.db_set("journal_entry", je_doc.name)
		frappe.db.commit()
		
		# Submit the JE
		je_doc.submit()
		
		frappe.msgprint(_("✅ JE created: {0} | Amount: {1} {2}").format(
			je_doc.name, amount, company_currency), indicator="green")
		
		return je_doc.name

	def ensure_account_currencies_match(self, bank_account, investor_account, target_currency):
		"""Ensure both accounts use the target currency"""
		try:
			# Update account currencies to match target
			frappe.db.set_value("Account", bank_account, "account_currency", target_currency)
			frappe.db.set_value("Account", investor_account, "account_currency", target_currency)
			frappe.db.commit()
			
			frappe.msgprint(_("🔧 Updated account currencies to {0}").format(target_currency), indicator="blue")
			
		except Exception as e:
			frappe.log_error(f"Currency update failed: {str(e)}", "Currency Update Error")

	def determine_je_company(self):
		"""ENHANCED: Smart company determination with currency priority"""
		# Get account companies
		bank_account_company = frappe.get_value("Account", self.amount_received_account, "company")
		investor_account_company = frappe.get_value("Account", self.investor_account, "company")
		invested_company = self.invested_company
		root_company = get_root_company(self.invested_company)
		
		# Get currencies
		invested_currency = frappe.get_cached_value("Company", invested_company, "default_currency")
		
		frappe.msgprint(_("🔍 Analysis:"), indicator="blue")
		frappe.msgprint(_("Bank: {0} ({1})").format(self.amount_received_account, bank_account_company))
		frappe.msgprint(_("Investor: {0} ({1})").format(self.investor_account, investor_account_company))
		frappe.msgprint(_("Target Currency: {0}").format(invested_currency))
		
		# PRIORITY 1: Both accounts in invested company (PERFECT)
		if bank_account_company == invested_company and investor_account_company == invested_company:
			return invested_company, "SAME_COMPANY_PERFECT"
		
		# PRIORITY 2: Invested company for currency alignment
		elif invested_company:
			return invested_company, "CURRENCY_ALIGNED"
		
		# PRIORITY 3: Both accounts in same company
		elif bank_account_company == investor_account_company:
			return bank_account_company, "SAME_COMPANY"
		
		# PRIORITY 4: Bank account's company
		elif bank_account_company:
			return bank_account_company, "BANK_FOCUS"
		
		# FALLBACK: Root company
		else:
			return root_company, "ROOT_FALLBACK"

	def create_simple_je(self, company, amount, posting_date, company_currency):
		"""FIXED: Create simple JE with exact amount from field"""
		# Ensure account currencies match
		self.ensure_account_currencies(company, company_currency)
		
		frappe.msgprint(_("💰 Creating JE with amount: {0}").format(amount), indicator="blue")
		
		je_doc = frappe.get_doc({
			"doctype": "Journal Entry",
			"company": company,
			"posting_date": posting_date,
			"user_remark": f"Auto-Investment by {self.investor_name} - {self.name}",
			"multi_currency": 0,
			"accounts": [
				{
					"account": self.amount_received_account,
					"debit_in_account_currency": amount,  # EXACT amount from field
					"credit_in_account_currency": 0,
					"user_remark": f"Cash from {self.investor_name}"
				},
				{
					"account": self.investor_account,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": amount,  # EXACT amount from field
					"user_remark": f"Investment by {self.investor_name}"
				}
			]
		})
		
		je_doc.flags.ignore_permissions = True
		je_doc.insert()
		self.db_set("journal_entry", je_doc.name)
		frappe.db.commit()
		je_doc.submit()
		
		frappe.msgprint(_("✅ Simple JE created: {0} with amount {1}").format(je_doc.name, amount), indicator="green")
		return je_doc.name

	def create_cross_company_je_bank_focus(self, amount, posting_date):
		"""FIXED: Cross-company JE with exact amount"""
		bank_account_company = frappe.get_value("Account", self.amount_received_account, "company")
		
		# Find or create equivalent investor account in bank's company
		equivalent_investor_account = self.find_or_create_equivalent_investor_account(bank_account_company)
		
		if equivalent_investor_account:
			# Create simple JE with equivalent account
			company_currency = frappe.get_cached_value("Company", bank_account_company, "default_currency")
			self.ensure_account_currencies(bank_account_company, company_currency)
			
			frappe.msgprint(_("💰 Cross-company JE with amount: {0}").format(amount), indicator="blue")
			
			je_doc = frappe.get_doc({
				"doctype": "Journal Entry",
				"company": bank_account_company,
				"posting_date": posting_date,
				"user_remark": f"Auto-Investment by {self.investor_name} - {self.name}",
				"multi_currency": 0,
				"accounts": [
					{
						"account": self.amount_received_account,
						"debit_in_account_currency": amount,  # EXACT amount from field
						"credit_in_account_currency": 0,
						"user_remark": f"Cash from {self.investor_name}"
					},
					{
						"account": equivalent_investor_account,
						"debit_in_account_currency": 0,
						"credit_in_account_currency": amount,  # EXACT amount from field
						"user_remark": f"Investment by {self.investor_name}"
					}
				]
			})
			
			je_doc.flags.ignore_permissions = True
			je_doc.insert()
			self.db_set("journal_entry", je_doc.name)
			frappe.db.commit()
			je_doc.submit()
			
			frappe.msgprint(_("✅ Cross-company JE created: {0} with amount {1}").format(je_doc.name, amount), indicator="green")
			return je_doc.name
		
		else:
			frappe.msgprint(_("⚠️ Could not create equivalent account. Manual JE required."), indicator="orange")
			return None

	def create_cross_company_je_investor_focus(self, amount, posting_date):
		"""FIXED: Investor focus JE with exact amount"""
		investor_account_company = frappe.get_value("Account", self.investor_account, "company")
		
		# Find equivalent bank account in investor's company
		equivalent_bank_account = self.find_equivalent_bank_account(investor_account_company)
		
		if equivalent_bank_account:
			# Update the amount received account to the equivalent one
			self.db_set("amount_received_account", equivalent_bank_account)
			
			company_currency = frappe.get_cached_value("Company", investor_account_company, "default_currency")
			self.ensure_account_currencies(investor_account_company, company_currency)
			
			frappe.msgprint(_("💰 Investor focus JE with amount: {0}").format(amount), indicator="blue")
			
			je_doc = frappe.get_doc({
				"doctype": "Journal Entry",
				"company": investor_account_company,
				"posting_date": posting_date,
				"user_remark": f"Auto-Investment by {self.investor_name} - {self.name}",
				"multi_currency": 0,
				"accounts": [
					{
						"account": equivalent_bank_account,
						"debit_in_account_currency": amount,  # EXACT amount from field
						"credit_in_account_currency": 0,
						"user_remark": f"Cash from {self.investor_name}"
					},
					{
						"account": self.investor_account,
						"debit_in_account_currency": 0,
						"credit_in_account_currency": amount,  # EXACT amount from field
						"user_remark": f"Investment by {self.investor_name}"
					}
				]
			})
			
			je_doc.flags.ignore_permissions = True
			je_doc.insert()
			self.db_set("journal_entry", je_doc.name)
			frappe.db.commit()
			je_doc.submit()
			
			frappe.msgprint(_("✅ Switched bank and created JE: {0} with amount {1}").format(je_doc.name, amount), indicator="green")
			frappe.msgprint(_("Bank account updated to: {0}").format(equivalent_bank_account), indicator="blue")
			return je_doc.name
		
		else:
			frappe.msgprint(_("⚠️ No compatible bank account found. Manual JE required."), indicator="orange")
			return None

	def find_or_create_equivalent_investor_account(self, target_company):
		"""Find or create equivalent investor account in target company"""
		try:
			# Generate account name for target company
			target_company_abbr = frappe.get_cached_value("Company", target_company, "abbr")
			if not target_company_abbr:
				target_company_abbr = target_company[:3].upper()
			
			if self.invested_project:
				equivalent_name = f"{self.investor_name}-{self.invested_project}-{target_company_abbr}"
			else:
				equivalent_name = f"{self.investor_name}-{target_company_abbr}"
			
			# Check if equivalent account exists
			existing_account = frappe.get_value("Account", {
				"account_name": equivalent_name,
				"company": target_company,
				"parent_account": ["like", "%Investor Capital%"]
			}, "name")
			
			if existing_account:
				frappe.msgprint(_("Found equivalent account: {0}").format(existing_account), indicator="green")
				return existing_account
			
			# Create equivalent account if it doesn't exist
			parent_account = frappe.db.get_value("Account", 
				{"account_name": "Investor Capital", "company": target_company, "is_group": 1}, "name")
			
			if not parent_account:
				parent_account = self.create_investor_capital_account_if_missing(target_company)
			
			account_number = self.generate_unique_account_number(target_company)
			company_currency = frappe.get_cached_value("Company", target_company, "default_currency")
			
			account_doc = frappe.get_doc({
				"doctype": "Account",
				"account_name": equivalent_name,
				"account_number": account_number,
				"parent_account": parent_account,
				"company": target_company,
				"account_type": "Equity",
				"root_type": "Equity",
				"is_group": 0,
				"account_currency": company_currency,
				"remarks": f"Equivalent investor account for {self.invested_company}"
			})
			
			account_doc.insert(ignore_permissions=True)
			frappe.msgprint(_("Created equivalent account: {0}").format(account_doc.name), indicator="green")
			return account_doc.name
			
		except Exception as e:
			frappe.log_error(f"Failed to create equivalent investor account: {str(e)}")
			return None

	def find_equivalent_bank_account(self, target_company):
		"""Find suitable bank account in target company"""
		try:
			# Look for any bank account in target company
			bank_accounts = frappe.get_all("Account", {
				"company": target_company,
				"account_type": ["in", ["Bank", "Cash"]],
				"is_group": 0
			}, ["name", "account_name"], limit=1)
			
			if bank_accounts:
				equivalent_bank = bank_accounts[0].name
				frappe.msgprint(_("Found equivalent bank: {0}").format(equivalent_bank), indicator="green")
				return equivalent_bank
			
			return None
			
		except Exception as e:
			frappe.log_error(f"Failed to find equivalent bank account: {str(e)}")
			return None

	def ensure_account_currencies(self, company, company_currency):
		"""Ensure both accounts have matching currencies"""
		try:
			# Update bank account currency
			frappe.db.set_value("Account", self.amount_received_account, "account_currency", company_currency)
			
			# Update investor account currency  
			frappe.db.set_value("Account", self.investor_account, "account_currency", company_currency)
			
			frappe.db.commit()
			
		except Exception as e:
			frappe.log_error(f"Currency update failed: {str(e)}", "Currency Update Error")

	def create_investor_capital_account_if_missing(self, company):
		"""Create Investor Capital structure"""
		existing = frappe.db.get_value("Account", {
			"account_name": "Investor Capital", 
			"company": company, 
			"is_group": 1
		}, "name")
		if existing:
			return existing
		
		# Find equity parent
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
		
		# Get company currency and available account number
		company_currency = frappe.get_cached_value("Company", company, "default_currency")
		existing_3110 = frappe.db.get_value("Account", {"account_number": "3110", "company": company}, "name")
		account_number = "3111" if existing_3110 else "3110"
		
		# Create Investor Capital account
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
		"""Generate unique account number"""
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

	def validate_company_account_structure(self):
		"""Enhanced validation with dynamic root company detection"""
		if not self.invested_company:
			frappe.throw(_("Invested Company is required"))
		
		root_company = get_root_company(self.invested_company)
		
		if not frappe.db.exists("Company", self.invested_company):
			frappe.throw(_("Invested Company {0} does not exist").format(self.invested_company))
		if not frappe.db.exists("Company", root_company):
			frappe.throw(_("Root Company {0} does not exist").format(root_company))

	@frappe.whitelist()
	def create_manual_journal_entry(self):
		"""Manual JE creation (fallback)"""
		if self.docstatus != 1:
			frappe.throw(_("Document must be submitted"))
		if self.journal_entry:
			frappe.throw(_("Journal entry already exists"))
		
		root_company = get_root_company(self.invested_company)
		
		return {
			"success": True,
			"message": "Create journal entry manually",
			"data": {
				"company": root_company,
				"invested_company": self.invested_company,
				"amount": self.invested_amount_company_currency,
				"bank_account": self.amount_received_account,
				"investor_account": self.investor_account
			}
		}

	@frappe.whitelist()
	def preview_account_structure(self):
		if not self.invested_company or not self.investor_name:
			return {"error": "Company and Investor Name required"}
		
		root_company = get_root_company(self.invested_company)
		
		existing = self.find_existing_investor_account(root_company)
		if existing:
			return {
				"action": "reuse", 
				"account_name": existing, 
				"root_company": root_company,
				"invested_company": self.invested_company,
				"message": f"Will reuse: {existing}"
			}
		
		account_name = self.generate_unique_account_name_with_abbr()
		account_number = self.generate_unique_account_number(root_company)
		
		return {
			"action": "create",
			"account_name": account_name,
			"account_number": account_number,
			"root_company": root_company,
			"invested_company": self.invested_company,
			"message": f"Will create: {account_number} - {account_name} in root company {root_company}"
		}

	@frappe.whitelist()
	def fix_account_structure(self):
		if not self.invested_company:
			return {"error": "Company required"}
		
		try:
			root_company = get_root_company(self.invested_company)
			
			existing = frappe.db.get_value("Account", {
				"account_name": "Investor Capital", 
				"company": root_company, 
				"is_group": 1
			}, "name")
			
			if existing:
				return {"success": True, "message": f"Already exists in {root_company}", "account": existing}
			
			result = self.create_investor_capital_account_if_missing(root_company)
			return {"success": True, "message": f"Created in {root_company}", "account": result}
		except Exception as e:
			return {"success": False, "error": str(e)}

# UTILITY FUNCTIONS
@frappe.whitelist()
def check_existing_investor_account(investor_name, invested_company, invested_project=None):
	try:
		root_company = get_root_company(invested_company)
		
		# Get company abbreviation
		company_abbr = frappe.get_cached_value("Company", invested_company, "abbr")
		if not company_abbr:
			company_abbr = invested_company[:3].upper()
		
		# Build search pattern with abbreviation
		if invested_project:
			account_name_pattern = f"{investor_name}-{invested_project}-{company_abbr}"
		else:
			account_name_pattern = f"{investor_name}-{company_abbr}"
		
		existing = frappe.get_value("Account", {
			"account_name": account_name_pattern,
			"company": root_company,
			"parent_account": ["like", "%Investor Capital%"]
		}, "name")
		
		if existing:
			return {
				"exists": True, 
				"account_name": existing, 
				"company": root_company,
				"invested_company": invested_company
			}
		else:
			return {
				"exists": False, 
				"new_account_name": account_name_pattern, 
				"company": root_company,
				"invested_company": invested_company
			}
	except Exception as e:
		return {"error": str(e)}

@frappe.whitelist()
def get_company_structure_info(company):
	if not company or not frappe.db.exists("Company", company):
		return {"error": "Invalid company"}
	
	try:
		root_company = get_root_company(company)
		is_root = (company == root_company)
		
		has_investor_capital = bool(frappe.db.get_value("Account", {
			"account_name": "Investor Capital", 
			"company": root_company, 
			"is_group": 1
		}, "name"))
		
		return {
			"company": company,
			"root_company": root_company,
			"is_root": is_root,
			"has_investor_capital": has_investor_capital
		}
	except Exception as e:
		return {"error": str(e)}

@frappe.whitelist()
def debug_company_hierarchy(company):
	"""Debug function to trace company hierarchy"""
	try:
		if not company:
			return {"error": "Company required"}
		
		hierarchy = []
		current = company
		
		while current:
			company_info = frappe.get_cached_value("Company", current, ["company_name", "is_group", "parent_company"])
			if not company_info:
				break
				
			hierarchy.append({
				"company": current,
				"name": company_info[0] if company_info else current,
				"is_group": bool(company_info[1]) if len(company_info) > 1 else False,
				"parent": company_info[2] if len(company_info) > 2 else None
			})
			
			current = company_info[2] if len(company_info) > 2 else None
			
			if len(hierarchy) > 10:  # Safety check
				break
		
		root_company = get_root_company(company)
		
		return {
			"success": True,
			"input_company": company,
			"root_company": root_company,
			"hierarchy": hierarchy,
			"depth": len(hierarchy)
		}
		
	except Exception as e:
		return {"error": str(e)}