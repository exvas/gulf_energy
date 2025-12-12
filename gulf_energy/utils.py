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

def fetch_project_from_investor(doc, method):
	"""
	Auto-fetch project from Investor when custom_investor field is set in Journal Entry.
	This function populates the project field and all account lines with the project from the investor.
	"""
	if doc.doctype != "Journal Entry":
		return
	
	# Check if custom_investor field exists and has a value
	if hasattr(doc, 'custom_investor') and doc.custom_investor:
		try:
			frappe.logger().info(f"🔍 Fetching project for Journal Entry from Investor: {doc.custom_investor}")
			
			# Get the investor record
			investor = frappe.get_doc("Investor", doc.custom_investor)
			frappe.logger().info(f"✅ Investor found: {investor.name}, Project: {investor.invested_project}")
			
			# Fetch the project from investor
			if investor.invested_project:
				# Set project at document level
				doc.project = investor.invested_project
				frappe.logger().info(f"✅ Project set at document level: {investor.invested_project}")
				
				# Set project in all account lines
				if hasattr(doc, 'accounts') and doc.accounts:
					for idx, row in enumerate(doc.accounts):
						row.project = investor.invested_project
						frappe.logger().info(f"✅ Project set in account line {idx}: {row.account} = {investor.invested_project}")
					frappe.logger().info(f"✅ Project set in all {len(doc.accounts)} accounting entries from Investor")
				else:
					frappe.logger().warning("⚠️ No accounting entries found in Journal Entry")
			else:
				frappe.logger().warning(f"⚠️ Investor {doc.custom_investor} does not have a project assigned")
		except frappe.DoesNotExistError:
			frappe.logger().warning(f"⚠️ Investor {doc.custom_investor} not found")
		except Exception as e:
			frappe.logger().error(f"❌ Error fetching project from investor: {str(e)}")
			frappe.log_error(f"Error fetching project from investor: {str(e)}", "Investor Project Fetch Error")

def validate_mandatory_project(doc, method):
	"""
	Validate that Project field is mandatory for Sales Invoice, Purchase Invoice,
	Journal Entry, and Payment Entry.
	"""
	# For Journal Entry, validate that all account lines have project set
	if doc.doctype == "Journal Entry":
		if hasattr(doc, 'accounts') and doc.accounts:
			for row in doc.accounts:
				if not row.project:
					frappe.throw(_("Project is mandatory for all account lines in Journal Entry"))
	
	# For other doctypes (Sales Invoice, Purchase Invoice, Payment Entry)
	elif hasattr(doc, 'project'):
		if not doc.project:
			frappe.throw(_("Project is mandatory for {0}").format(doc.doctype))
