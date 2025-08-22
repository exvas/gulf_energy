import frappe
from gulf_energy.gulf_energy.doctype.investor.investor import Investor

# Test creating a new investor document to verify method accessibility
investor = frappe.new_doc('Investor')
investor.investor_name = 'Test Investor Fix'
investor.invested_project = 'Test Project'

# Test the method that was previously causing the error
try:
    account_name = investor.generate_unique_account_name()
    print(f'SUCCESS: Account name generated: {account_name}')
    print('✅ The "object has no attribute generate_unique_account_name" error is FIXED!')
except Exception as e:
    print(f'ERROR: {str(e)}')
    print('❌ The error still exists')
