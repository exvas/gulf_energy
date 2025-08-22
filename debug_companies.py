#!/usr/bin/env python3

# Test script to debug the multi-company account creation issue
import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'apps'))

try:
    import frappe
    frappe.init(site='gulf')
    frappe.connect()
    
    from gulf_energy.gulf_energy.doctype.investor.investor import debug_company_accounts
    
    # Test the problematic companies
    companies_to_test = [
        "Hauler Petrochemical FZC",
        "Gulf Energy Trading Company"
    ]
    
    print("🔍 Debugging Multi-Company Account Structure")
    print("=" * 60)
    
    for company in companies_to_test:
        print(f"\n📊 Company: {company}")
        print("-" * 40)
        
        result = debug_company_accounts(company)
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Company exists: {company}")
            print(f"💰 Default Currency: {result.get('company_currency', 'N/A')}")
            print(f"🏛️ Root Accounts: {result.get('total_root_accounts', 0)}")
            print(f"📈 Equity Accounts: {result.get('total_equity_accounts', 0)}")
            print(f"👥 Has Investor Capital: {result.get('has_investor_capital', False)}")
            
            if result.get('equity_accounts'):
                print("\n📋 Equity Account Structure:")
                for acc in result['equity_accounts']:
                    group_indicator = "📁" if acc['is_group'] else "📄"
                    print(f"   {group_indicator} {acc['account_name']} ({acc.get('account_number', 'No Number')})")
    
    print("\n✅ Debug complete! Use this information to identify account structure issues.")
    
except Exception as e:
    print(f"❌ Error running debug: {str(e)}")
    import traceback
    traceback.print_exc()
