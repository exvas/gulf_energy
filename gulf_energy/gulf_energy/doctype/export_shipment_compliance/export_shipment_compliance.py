# Copyright (c) 2026, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


class ExportShipmentCompliance(Document):
	def validate(self):
		self.calculate_totals()
		self.update_document_upload_status()
		self.run_compliance_checks()
		self.update_compliance_status()

	def on_submit(self):
		self.validate_mandatory_documents()
		self.validate_hazardous_items_msds()
		self.status = "Submitted"

	def on_cancel(self):
		self.status = "Draft"

	def calculate_totals(self):
		"""Calculate total containers, gross weight, and net weight from containers table."""
		self.total_containers = len(self.containers) if self.containers else 0
		self.total_gross_weight = flt(
			sum(flt(row.gross_weight) for row in self.containers), 2
		) if self.containers else 0
		self.total_net_weight = flt(
			sum(flt(row.net_weight) for row in self.containers), 2
		) if self.containers else 0

	def update_document_upload_status(self):
		"""Auto-set is_uploaded flag based on whether attachment exists."""
		for row in self.shipping_documents:
			row.is_uploaded = 1 if row.attachment else 0

	def run_compliance_checks(self):
		"""Evaluate each checklist item and set is_compliant flag."""
		for row in self.compliance_checklist:
			row.is_compliant = self._evaluate_check(row.check_item)
			if row.is_compliant and not row.checked_by:
				row.checked_by = frappe.session.user
				row.checked_date = today()

	def _evaluate_check(self, check_item):
		"""Evaluate a single compliance check item. Returns 1 if compliant, 0 otherwise."""
		checks = {
			"B/L number is present": lambda: 1 if self.bl_number else 0,
			"Country of Origin is filled": lambda: 1 if self.country_of_origin else 0,
			"Country of Destination is filled": lambda: 1 if self.country_of_destination else 0,
			"IEC number is present": lambda: 1 if self.iec_number else 0,
			"All mandatory shipping documents uploaded": self._check_mandatory_docs,
			"MSDS available for hazardous items": self._check_hazardous_msds,
			"Export license available": self._check_export_license,
		}

		evaluator = checks.get(check_item)
		if evaluator:
			return evaluator()
		return 0

	def _check_mandatory_docs(self):
		"""Check if all mandatory shipping documents have attachments."""
		for row in self.shipping_documents:
			if row.is_mandatory and not row.attachment:
				return 0
		return 1 if self.shipping_documents else 0

	def _check_hazardous_msds(self):
		"""Check if all hazardous items in containers have active MSDS."""
		from gulf_energy.gulf_energy.doctype.msds_register.msds_register import get_active_msds

		has_hazardous = False
		for row in self.containers:
			if not row.item_code:
				continue
			is_hazardous = frappe.db.get_value("Item", row.item_code, "custom_is_hazardous")
			if is_hazardous:
				has_hazardous = True
				active_msds = get_active_msds(row.item_code)
				if not active_msds:
					return 0
		# If no hazardous items, this check is N/A — mark as compliant
		return 1 if has_hazardous else 1

	def _check_export_license(self):
		"""Check if export license is present when items require it."""
		for row in self.containers:
			if not row.item_code:
				continue
			requires_license = frappe.db.get_value(
				"Item", row.item_code, "custom_export_license_required"
			)
			if requires_license and not self.export_license_no:
				return 0
		return 1

	def update_compliance_status(self):
		"""Update overall compliance status based on checklist."""
		if not self.compliance_checklist:
			self.compliance_status = "Pending"
			return

		total = len(self.compliance_checklist)
		compliant = sum(1 for row in self.compliance_checklist if row.is_compliant)

		if compliant == 0:
			self.compliance_status = "Pending"
		elif compliant < total:
			self.compliance_status = "Partial"
		else:
			self.compliance_status = "Complete"

	def validate_mandatory_documents(self):
		"""On submit: ensure all mandatory documents are uploaded."""
		missing = []
		for row in self.shipping_documents:
			if row.is_mandatory and not row.attachment:
				missing.append(row.document_type)

		if missing:
			frappe.throw(
				_("The following mandatory documents are not uploaded: {0}").format(
					", ".join(missing)
				),
				title=_("Missing Documents"),
			)

	def validate_hazardous_items_msds(self):
		"""On submit: block if hazardous items don't have active MSDS."""
		from gulf_energy.gulf_energy.doctype.msds_register.msds_register import get_active_msds

		for row in self.containers:
			if not row.item_code:
				continue
			is_hazardous = frappe.db.get_value("Item", row.item_code, "custom_is_hazardous")
			if is_hazardous:
				active_msds = get_active_msds(row.item_code)
				if not active_msds:
					frappe.throw(
						_("Item {0} in Container {1} is hazardous but has no active MSDS. "
						  "Please upload MSDS in the MSDS Register before submitting.").format(
							row.item_code, row.container_no
						),
						title=_("MSDS Compliance Failed"),
					)


@frappe.whitelist()
def auto_populate_checklist(docname):
	"""Generate default compliance checklist items for the shipment."""
	doc = frappe.get_doc("Export Shipment Compliance", docname)

	default_checks = [
		"B/L number is present",
		"Country of Origin is filled",
		"Country of Destination is filled",
		"IEC number is present",
		"All mandatory shipping documents uploaded",
	]

	# Add hazardous check if any container has hazardous items
	has_hazardous = False
	has_export_license_items = False
	for row in doc.containers:
		if row.item_code:
			item_flags = frappe.db.get_value(
				"Item", row.item_code,
				["custom_is_hazardous", "custom_export_license_required"],
				as_dict=True,
			)
			if item_flags:
				if item_flags.custom_is_hazardous:
					has_hazardous = True
				if item_flags.custom_export_license_required:
					has_export_license_items = True

	if has_hazardous:
		default_checks.append("MSDS available for hazardous items")
	if has_export_license_items:
		default_checks.append("Export license available")

	# Clear existing checklist and add new items
	doc.compliance_checklist = []
	for check in default_checks:
		doc.append("compliance_checklist", {
			"check_item": check,
			"is_compliant": 0,
		})

	doc.save()
	return doc.name


@frappe.whitelist()
def validate_compliance(docname):
	"""Run compliance checks and return updated status."""
	doc = frappe.get_doc("Export Shipment Compliance", docname)
	doc.run_compliance_checks()
	doc.update_compliance_status()
	doc.save()
	return {
		"compliance_status": doc.compliance_status,
		"message": _("Compliance validation completed. Status: {0}").format(
			doc.compliance_status
		),
	}
