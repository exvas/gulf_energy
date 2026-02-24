# Copyright (c) 2026, sammish and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Create Workflow for Export Shipment Compliance doctype."""

	# Skip if workflow already exists
	if frappe.db.exists("Workflow", "Export Shipment Compliance Workflow"):
		return

	# Create Workflow States if they don't exist
	for state in ["Draft", "Pending Review", "Approved", "Submitted", "Closed", "Rejected"]:
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc({
				"doctype": "Workflow State",
				"workflow_state_name": state,
			}).insert(ignore_permissions=True)

	# Create Workflow Actions if they don't exist
	for action in ["Submit for Review", "Approve", "Reject", "Submit", "Close", "Reopen"]:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({
				"doctype": "Workflow Action Master",
				"workflow_action_name": action,
			}).insert(ignore_permissions=True)

	workflow = frappe.get_doc({
		"doctype": "Workflow",
		"workflow_name": "Export Shipment Compliance Workflow",
		"document_type": "Export Shipment Compliance",
		"is_active": 1,
		"override_status": 1,
		"send_email_alert": 0,
		"states": [
			{
				"state": "Draft",
				"doc_status": "0",
				"allow_edit": "Stock Manager",
				"is_optional_state": 0,
			},
			{
				"state": "Pending Review",
				"doc_status": "0",
				"allow_edit": "Stock Manager",
				"is_optional_state": 0,
			},
			{
				"state": "Approved",
				"doc_status": "0",
				"allow_edit": "Stock Manager",
				"is_optional_state": 0,
			},
			{
				"state": "Rejected",
				"doc_status": "0",
				"allow_edit": "Stock Manager",
				"is_optional_state": 0,
			},
			{
				"state": "Submitted",
				"doc_status": "1",
				"allow_edit": "System Manager",
				"is_optional_state": 0,
			},
			{
				"state": "Closed",
				"doc_status": "1",
				"allow_edit": "System Manager",
				"is_optional_state": 0,
			},
		],
		"transitions": [
			{
				"state": "Draft",
				"action": "Submit for Review",
				"next_state": "Pending Review",
				"allowed": "Stock Manager",
				"allow_self_approval": 1,
			},
			{
				"state": "Pending Review",
				"action": "Approve",
				"next_state": "Approved",
				"allowed": "Stock Manager",
				"allow_self_approval": 1,
			},
			{
				"state": "Pending Review",
				"action": "Reject",
				"next_state": "Rejected",
				"allowed": "Stock Manager",
				"allow_self_approval": 1,
			},
			{
				"state": "Rejected",
				"action": "Reopen",
				"next_state": "Draft",
				"allowed": "Stock Manager",
				"allow_self_approval": 1,
			},
			{
				"state": "Approved",
				"action": "Submit",
				"next_state": "Submitted",
				"allowed": "Stock Manager",
				"allow_self_approval": 1,
			},
			{
				"state": "Submitted",
				"action": "Close",
				"next_state": "Closed",
				"allowed": "Stock Manager",
				"allow_self_approval": 1,
			},
		],
	})
	workflow.insert(ignore_permissions=True)
	frappe.db.commit()
