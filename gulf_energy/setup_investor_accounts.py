# Setup Script for Gulf Energy Investor Module

import frappe
from frappe import _

def setup_investor_accounts(company):
    """Setup the required account structure for investor module"""
    
    # Check if 3000 - Equity exists
    equity_account = frappe.get_value("Account", 
        {"account_number": "3000", "company": company}, 
        "name")
    
    if not equity_account:
        # Create main equity account if it doesn't exist
        equity_doc = frappe.get_doc({
            "doctype": "Account",
            "account_name": "Equity",
            "account_number": "3000",
            "company": company,
            "account_type": "Equity",
            "root_type": "Equity",
            "is_group": 1
        })
        equity_doc.insert(ignore_permissions=True)
        equity_account = equity_doc.name
    
    # Check if 3110 - Investor Capital exists
    investor_capital = frappe.get_value("Account", 
        {"account_number": "3110", "company": company}, 
        "name")
    
    if not investor_capital:
        # Create investor capital account
        investor_capital_doc = frappe.get_doc({
            "doctype": "Account",
            "account_name": "Investor Capital",
            "account_number": "3110",
            "parent_account": equity_account,
            "company": company,
            "account_type": "Equity",
            "root_type": "Equity",
            "is_group": 1
        })
        investor_capital_doc.insert(ignore_permissions=True)
        print(f"Created Investor Capital account for {company}")
    else:
        print(f"Investor Capital account already exists for {company}")

def setup_for_all_companies():
    """Setup investor accounts for all companies"""
    companies = frappe.get_all("Company", fields=["name"])
    
    for company in companies:
        try:
            setup_investor_accounts(company.name)
        except Exception as e:
            print(f"Failed to setup investor accounts for {company.name}: {str(e)}")

if __name__ == "__main__":
    setup_for_all_companies()
