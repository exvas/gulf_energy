#!/usr/bin/env python3

# Simple debug script to understand the account structure issue
# Run this using: bench --site gulf console
# Then: exec(open('apps/gulf_energy/debug_simple.py').read())

print("🔍 Debugging Account Structure Issue")
print("=" * 50)

companies = ["Gulf Energy Trading Company", "Hauler Petrochemical FZC"]

for company in companies:
    print(f"\n🏢 Company: {company}")
    print("-" * 30)
    
    # Check if company exists
    if not frappe.db.exists("Company", company):
        print(f"❌ Company does not exist!")
        continue
    
    # Check Investor Capital
    investor_capital = frappe.db.get_value("Account", {
        "account_name": "Investor Capital",
        "company": company,
        "is_group": 1
    }, ["name", "parent_account"])
    
    if investor_capital:
        print(f"✅ Investor Capital: {investor_capital[0]}")
        print(f"   Parent: {investor_capital[1] or 'ROOT'}")
    else:
        print(f"❌ No Investor Capital found")
        
        # Show available equity accounts
        equity_accounts = frappe.get_all("Account", {
            "company": company,
            "root_type": "Equity",
            "is_group": 1
        }, ["name", "account_name", "parent_account"])
        
        print(f"📊 Available Equity Accounts ({len(equity_accounts)}):")
        for acc in equity_accounts:
            print(f"   - {acc.account_name}")
            print(f"     Full Name: {acc.name}")
            print(f"     Parent: {acc.parent_account or 'ROOT'}")
    
    print()

print("🎯 SOLUTION:")
print("Each company needs its own 'Investor Capital' group account.")
print("The error occurs because ERPNext tries to use the account from")
print("'Gulf Energy Trading Company' for 'Hauler Petrochemical FZC'")
print("which violates the same-company rule.")
