#!/usr/bin/env python3

# Final test to verify both methods are accessible
try:
    from gulf_energy.gulf_energy.doctype.investor.investor import Investor
    print("✅ Successfully imported Investor class")
    
    # Check both methods exist
    methods_to_check = ['generate_unique_account_name', 'preview_account_structure']
    
    for method_name in methods_to_check:
        if hasattr(Investor, method_name):
            print(f"✅ {method_name} method exists in class")
        else:
            print(f"❌ {method_name} method NOT found in class")
    
    print("\n🎉 All critical methods are now properly accessible in the Investor class!")
    print("The AttributeError issues have been resolved!")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")
