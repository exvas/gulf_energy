#!/usr/bin/env python3
import os
import sys

# Add the bench path to sys.path
sys.path.insert(0, '/Users/sammishthundiyil/frappe-bench-general')
sys.path.insert(0, '/Users/sammishthundiyil/frappe-bench-general/apps')

# Set environment variables
os.environ['FRAPPE_SITE'] = 'safaqatar.local'

try:
    import frappe
    frappe.init(site='safaqatar.local')
    frappe.connect()
    
    # Test the Investor class and method accessibility
    from gulf_energy.gulf_energy.doctype.investor.investor import Investor
    
    # Create an Investor instance
    investor = Investor()
    investor.investor_name = 'Test Investor'
    investor.invested_project = 'Test Project'
    investor.invested_company = 'Gulf Energy Company'
    
    # Test method accessibility
    try:
        account_name = investor.generate_unique_account_name()
        print('SUCCESS: generate_unique_account_name method is accessible')
        print(f'Generated account name: {account_name}')
        
        # Test account number generation
        try:
            existing_accounts = frappe.get_all("Account",
                filters={
                    "company": investor.invested_company,
                    "parent_account": ["like", "%Investor Capital%"],
                    "account_number": ["like", "I30%"]
                },
                fields=["account_number"],
                order_by="account_number"
            )
            print(f'Found {len(existing_accounts)} existing investor accounts')
            
            account_number = investor.generate_unique_account_number()
            print(f'Generated account number: {account_number}')
            print('SUCCESS: Both methods are working correctly!')
            
        except Exception as e:
            print(f'ERROR in generate_unique_account_number: {str(e)}')
            
    except AttributeError as e:
        print(f'ERROR: Method not accessible - {str(e)}')
    except Exception as e:
        print(f'ERROR: {str(e)}')
        
finally:
    frappe.destroy()

print('Test completed.')
