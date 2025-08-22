# Quick fix for multi-company account issue
# Run this in bench console: exec(open('apps/gulf_energy/quick_fix.py').read())

print("🔧 Quick Fix: Creating Investor Capital accounts for all companies")

companies = ["Gulf Energy Trading Company", "Hauler Petrochemical FZC"]

for company_name in companies:
    print(f"\n📋 Processing: {company_name}")
    
    # Check if Investor Capital exists
    existing = frappe.db.get_value("Account", {
        "account_name": "Investor Capital",
        "company": company_name,
        "is_group": 1
    }, "name")
    
    if existing:
        print(f"✅ Already exists: {existing}")
        continue
    
    # Find parent equity account
    equity_parent = frappe.db.get_value("Account", {
        "company": company_name,
        "root_type": "Equity",
        "is_group": 1
    }, "name")
    
    if not equity_parent:
        print(f"❌ No equity account found for {company_name}")
        continue
    
    try:
        # Create Investor Capital
        doc = frappe.get_doc({
            "doctype": "Account",
            "account_name": "Investor Capital",
            "account_number": "3110",
            "parent_account": equity_parent,
            "company": company_name,
            "account_type": "Equity",
            "root_type": "Equity",
            "is_group": 1,
            "account_currency": frappe.get_cached_value("Company", company_name, "default_currency")
        })
        doc.insert(ignore_permissions=True)
        print(f"✅ Created: {doc.name}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

print("\n🎉 Fix complete! Try creating investor records now.")
