# Test the debug function using bench console
from gulf_energy.gulf_energy.doctype.investor.investor import debug_company_accounts

# Test the problematic companies
companies = ["Hauler Petrochemical FZC", "Gulf Energy Trading Company"]

for company in companies:
    print(f"\n=== Debugging {company} ===")
    result = debug_company_accounts(company)
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Company: {company}")
        print(f"Currency: {result.get('company_currency', 'N/A')}")
        print(f"Root Accounts: {result.get('total_root_accounts', 0)}")
        print(f"Equity Accounts: {result.get('total_equity_accounts', 0)}")
        print(f"Has Investor Capital: {result.get('has_investor_capital', False)}")
        
        if result.get('equity_accounts'):
            print("Equity Accounts:")
            for acc in result['equity_accounts']:
                group_text = "[GROUP]" if acc['is_group'] else "[ACCOUNT]"
                print(f"  {group_text} {acc['account_name']} (#{acc.get('account_number', 'No Number')})")
