import frappe
from frappe import _
import sys

def test_investor_je_flow():
    """
    Test that when an Investor is submitted, the auto-created Journal Entry
    has both project and custom_investor fields populated.
    """
    
    print("🧪 Testing Investor -> Journal Entry flow...")
    
    # Check if custom_investor field exists in Journal Entry
    custom_field_exists = frappe.db.exists("Custom Field", {
        "dt": "Journal Entry",
        "fieldname": "custom_investor"
    })
    
    if not custom_field_exists:
        print("❌ Custom field 'custom_investor' does not exist in Journal Entry")
        print("   Running patch to create it...")
        
        # Import and run the patch
        from gulf_energy.patches.add_custom_investor_field_to_je import execute
        execute()
        print("✅ Patch executed")
    
    # Create a test investor
    print("📝 Creating test investor...")
    
    # Get a test company
    companies = frappe.get_all("Company", limit=1)
    if not companies:
        print("❌ No companies found in the system")
        return
    
    company = companies[0].name
    
    # Get a test project
    projects = frappe.get_all("Project", limit=1)
    if not projects:
        print("⚠️ No projects found, creating a test project...")
        project_doc = frappe.get_doc({
            "doctype": "Project",
            "project_name": "Test Project for Investor",
            "status": "Open"
        })
        project_doc.insert()
        project = project_doc.name
    else:
        project = projects[0].name
    
    # Get a bank account
    bank_accounts = frappe.get_all("Account", 
        filters={"account_type": "Bank", "company": company, "is_group": 0},
        limit=1
    )
    
    if not bank_accounts:
        print("❌ No bank accounts found for company")
        return
    
    bank_account = bank_accounts[0].name
    
    # Create investor
    investor_doc = frappe.get_doc({
        "doctype": "Investor",
        "investor_name": "Test Investor JE Flow",
        "invested_company": company,
        "invested_project": project,
        "invested_amount": 10000,
        "exchange_rate": 1,
        "amount_received_account": bank_account,
        "dividend": 5
    })
    
    investor_doc.insert()
    print(f"✅ Investor created: {investor_doc.name}")
    
    # Submit the investor (this should auto-create JE)
    print("🔄 Submitting investor...")
    investor_doc.submit()
    
    # Check if journal entry was created
    if investor_doc.journal_entry:
        print(f"✅ Journal Entry created: {investor_doc.journal_entry}")
        
        # Get the journal entry
        je_doc = frappe.get_doc("Journal Entry", investor_doc.journal_entry)
        
        # Check project field
        if je_doc.project == project:
            print(f"✅ Project field correctly set: {je_doc.project}")
        else:
            print(f"❌ Project field not set correctly. Expected: {project}, Got: {je_doc.project}")
        
        # Check custom_investor field
        if hasattr(je_doc, 'custom_investor'):
            if je_doc.custom_investor == investor_doc.name:
                print(f"✅ custom_investor field correctly set: {je_doc.custom_investor}")
            else:
                print(f"❌ custom_investor field not set correctly. Expected: {investor_doc.name}, Got: {je_doc.custom_investor}")
        else:
            print("❌ custom_investor field does not exist on Journal Entry document")
        
        # Check account lines have project
        all_lines_have_project = all(row.project == project for row in je_doc.accounts if row.project)
        if all_lines_have_project:
            print("✅ All account lines have project set")
        else:
            print("❌ Some account lines missing project")
            
        # Print summary
        print("\n📊 SUMMARY:")
        print(f"   Investor: {investor_doc.name}")
        print(f"   Journal Entry: {je_doc.name}")
        print(f"   Project: {je_doc.project}")
        print(f"   custom_investor: {getattr(je_doc, 'custom_investor', 'NOT SET')}")
        print(f"   JE Status: {je_doc.docstatus}")
        
    else:
        print("❌ No journal entry was created")
    
    # Cleanup
    print("\n🧹 Cleaning up test data...")
    try:
        if investor_doc.journal_entry:
            je = frappe.get_doc("Journal Entry", investor_doc.journal_entry)
            if je.docstatus == 1:
                je.cancel()
            frappe.delete_doc("Journal Entry", investor_doc.journal_entry)
        
        investor_doc.cancel()
        frappe.delete_doc("Investor", investor_doc.name)
        
        # Delete test project if we created it
        if 'projects' not in locals() or not projects:
            frappe.delete_doc("Project", project)
            
        print("✅ Test data cleaned up")
    except Exception as e:
        print(f"⚠️ Cleanup error (ignored): {e}")
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    # Initialize frappe
    frappe.init(site="test_site")  # You may need to adjust this
    frappe.connect()
    
    try:
        test_investor_je_flow()
    finally:
        frappe.destroy()