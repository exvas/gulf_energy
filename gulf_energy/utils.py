import frappe
from frappe import _

@frappe.whitelist()
def setup_company_investor_structure(company):
    """
    Utility function to manually set up investor account structure for a company.
    Can be called via: /api/method/gulf_energy.utils.setup_company_investor_structure?company=Your Company Name
    """
    if not company:
        return {"error": "Company parameter is required"}
    
    if not frappe.db.exists("Company", company):
        return {"error": f"Company '{company}' does not exist"}
    
    try:
        # Check if Investor Capital already exists
        existing_investor_capital = frappe.db.get_value("Account", {
            "account_name": "Investor Capital",
            "company": company,
            "is_group": 1
        }, "name")
        
        if existing_investor_capital:
            return {
                "success": True,
                "message": f"Investor Capital account already exists for {company}",
                "account": existing_investor_capital
            }
        
        # Find suitable parent equity account
        equity_accounts = frappe.get_all("Account", {
            "company": company,
            "root_type": "Equity",
            "is_group": 1
        }, ["name", "account_name", "parent_account"], order_by="lft")
        
        if not equity_accounts:
            return {"error": f"No equity accounts found for company {company}. Please ensure Chart of Accounts is set up properly."}
        
        # Use the first equity account as parent (usually the root equity account)
        parent_equity = equity_accounts[0].name
        
        # Create Investor Capital account
        investor_capital_doc = frappe.get_doc({
            "doctype": "Account",
            "account_name": "Investor Capital",
            "account_number": "3110",
            "parent_account": parent_equity,
            "company": company,
            "account_type": "Equity",
            "root_type": "Equity",
            "is_group": 1,
            "account_currency": frappe.get_cached_value("Company", company, "default_currency")
        })
        
        investor_capital_doc.insert(ignore_permissions=True)
        
        return {
            "success": True,
            "message": f"Successfully created Investor Capital account for {company}",
            "account": investor_capital_doc.name,
            "parent": parent_equity
        }
        
    except Exception as e:
        frappe.log_error(f"Error setting up investor structure for {company}: {str(e)}")
        return {"error": str(e)}

@frappe.whitelist()
def fix_hauler_accounts():
    """Quick fix specifically for Hauler Petrochemical FZC"""
    return setup_company_investor_structure("Hauler Petrochemical FZC")
