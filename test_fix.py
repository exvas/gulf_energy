#!/usr/bin/env python3

# Simple test to verify the Investor class fix
try:
    from gulf_energy.gulf_energy.doctype.investor.investor import Investor
    print("✅ Successfully imported Investor class")
    
    # Check if the method exists
    if hasattr(Investor, 'generate_unique_account_name'):
        print("✅ generate_unique_account_name method exists in class")
    else:
        print("❌ generate_unique_account_name method NOT found in class")
        
    # List all methods in the class
    methods = [method for method in dir(Investor) if not method.startswith('_')]
    print(f"📋 Available methods: {', '.join(methods)}")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")
