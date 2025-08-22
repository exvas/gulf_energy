#!/usr/bin/env python3
"""
Direct fix script for multi-company account creation issue
This script will manually create the required account structure for Hauler Petrochemical FZC
"""

import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'apps'))

try:
    import frappe
    frappe.init(site='gulf')
    frappe.connect()
    
    def create_investor_capital_for_company(company_name):
        """Manually create Investor Capital account for a specific company"""
        print(f"🔧 Setting up Investor Capital for: {company_name}")
        
        # Check if company exists
        if not frappe.db.exists("Company", company_name):
            print(f"❌ Company {company_name} does not exist")
            return False
            
        # Check if Investor Capital already exists
        existing = frappe.db.get_value("Account", {
            "account_name": "Investor Capital",
            "company": company_name,
            "is_group": 1
        }, "name")
        
        if existing:
            print(f"✅ Investor Capital already exists: {existing}")
            return existing
            
        print(f"❌ No Investor Capital found. Creating for {company_name}...")
        
        # Find equity parent account for this company
        equity_accounts = frappe.get_all("Account", {
            "company": company_name,
            "root_type": "Equity",
            "is_group": 1
        }, ["name", "account_name", "parent_account", "account_number"], order_by="lft")
        
        print(f"📊 Found {len(equity_accounts)} equity accounts for {company_name}")
        for acc in equity_accounts:
            print(f"   - {acc.account_name} (#{acc.account_number or 'No Number'}) [Group: {acc.parent_account or 'ROOT'}]")
        
        if not equity_accounts:
            print(f"❌ No equity accounts found for {company_name}")
            return False
            
        # Use the first equity account as parent
        parent_account = equity_accounts[0].name
        print(f"🎯 Using parent account: {equity_accounts[0].account_name}")
        
        try:
            # Create Investor Capital account
            investor_capital_doc = frappe.get_doc({
                "doctype": "Account",
                "account_name": "Investor Capital",
                "account_number": "3110",
                "parent_account": parent_account,
                "company": company_name,
                "account_type": "Equity",
                "root_type": "Equity",
                "is_group": 1,
                "account_currency": frappe.get_cached_value("Company", company_name, "default_currency")
            })
            
            investor_capital_doc.insert(ignore_permissions=True)
            print(f"✅ Successfully created: {investor_capital_doc.name}")
            return investor_capital_doc.name
            
        except Exception as e:
            print(f"❌ Error creating Investor Capital: {str(e)}")
            return False
    
    # Main execution
    print("🚀 Starting Multi-Company Account Fix")
    print("=" * 50)
    
    # Test both companies
    companies = [
        "Gulf Energy Trading Company",
        "Hauler Petrochemical FZC"
    ]
    
    for company in companies:
        print(f"\n📋 Processing: {company}")
        print("-" * 40)
        result = create_investor_capital_for_company(company)
        
        if result:
            print(f"✅ {company}: Ready for investor accounts")
        else:
            print(f"❌ {company}: Needs manual setup")
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Try creating the investor record again")
    print("2. Each company should now have its own Investor Capital account")
    print("3. No more cross-company account errors!")
    
except Exception as e:
    print(f"❌ Script error: {str(e)}")
    import traceback
    traceback.print_exc()
