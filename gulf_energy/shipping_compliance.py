# Copyright (c) 2026, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def validate_item_msds_compliance(doc, method):
	"""On Item validate: warn if item is marked as MSDS Required
	but has no active MSDS in the MSDS Register."""

	if not doc.custom_msds_required:
		return

	from gulf_energy.gulf_energy.doctype.msds_register.msds_register import get_active_msds

	active_msds = get_active_msds(doc.name)
	if not active_msds:
		frappe.msgprint(
			_("Item {0} requires MSDS but no active MSDS record was found in the MSDS Register. "
			  "Please create or update the MSDS record.").format(doc.item_code or doc.name),
			indicator="orange",
			title=_("MSDS Compliance Warning"),
		)


def get_hazardous_items_in_shipment(doc):
	"""Return list of hazardous item codes from containers in an Export Shipment Compliance doc."""
	hazardous_items = []
	for row in doc.containers or []:
		if not row.item_code:
			continue
		is_hazardous = frappe.db.get_value("Item", row.item_code, "custom_is_hazardous")
		if is_hazardous:
			hazardous_items.append({
				"item_code": row.item_code,
				"container_no": row.container_no,
			})
	return hazardous_items


def validate_shipment_documents(doc):
	"""Check all mandatory shipping documents are uploaded. Returns list of missing doc types."""
	missing = []
	for row in doc.shipping_documents or []:
		if row.is_mandatory and not row.attachment:
			missing.append(row.document_type)
	return missing
