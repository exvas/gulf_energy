import frappe
from frappe import _

def execute():
	"""
	Patch to add custom_investor field to Journal Entry doctype.
	This field links the Journal Entry to the Investor record that created it.
	"""
	
	# Check if Journal Entry doctype exists
	if not frappe.db.exists("DocType", "Journal Entry"):
		frappe.logger().warning("Journal Entry doctype does not exist yet. Skipping custom field creation.")
		return
	
	# Check if custom field already exists
	existing_field = frappe.db.exists("Custom Field", {
		"dt": "Journal Entry",
		"fieldname": "custom_investor"
	})
	
	if existing_field:
		frappe.logger().info("Custom field 'custom_investor' already exists in Journal Entry")
		return
	
	try:
		# Create the custom field
		custom_field = frappe.get_doc({
			"doctype": "Custom Field",
			"dt": "Journal Entry",
			"fieldname": "custom_investor",
			"label": "Investor",
			"fieldtype": "Link",
			"options": "Investor",
			"insert_after": "user_remark",
			"read_only": 0,
			"reqd": 0,
			"hidden": 0,
			"fetch_from": None,
			"fetch_if_empty": 0,
			"allow_on_submit": 1,
			"description": "Links the Journal Entry to the Investor record that created it"
		})
		
		custom_field.insert(ignore_permissions=True)
		frappe.db.commit()
		
		frappe.logger().info("✅ Successfully created custom_investor field in Journal Entry")
		
		# Rebuild the doctype to apply changes
		frappe.clear_cache()
		
	except Exception as e:
		frappe.logger().error(f"❌ Error creating custom_investor field: {str(e)}")
		frappe.log_error(f"Error creating custom_investor field: {str(e)}", "Custom Field Creation Error")
		raise