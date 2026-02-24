# Copyright (c) 2026, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class MSDSRegister(Document):
	def validate(self):
		self.validate_dates()
		self.update_status_on_expiry()
		self.validate_item_requires_msds()

	def validate_dates(self):
		"""Ensure expiry_date is after valid_from."""
		if self.valid_from and self.expiry_date:
			if getdate(self.expiry_date) <= getdate(self.valid_from):
				frappe.throw(
					_("Expiry Date must be after Valid From date"),
					title=_("Invalid Date Range"),
				)

	def update_status_on_expiry(self):
		"""Auto-set status to Expired if expiry_date has passed."""
		if self.expiry_date and getdate(self.expiry_date) < getdate(today()):
			if self.status != "Expired":
				self.status = "Expired"
				frappe.msgprint(
					_("MSDS status set to Expired as the expiry date has passed."),
					indicator="orange",
				)

	def validate_item_requires_msds(self):
		"""Warn if the linked item does not have custom_msds_required checked."""
		if self.item_code:
			msds_required = frappe.db.get_value("Item", self.item_code, "custom_msds_required")
			if not msds_required:
				frappe.msgprint(
					_("Note: Item {0} does not have 'MSDS Required' flag enabled.").format(
						self.item_code
					),
					indicator="blue",
				)

	def on_load(self):
		"""Check expiry status when the document is loaded."""
		if self.expiry_date and getdate(self.expiry_date) < getdate(today()):
			if self.status != "Expired":
				self.db_set("status", "Expired", update_modified=False)
				self.status = "Expired"


def get_active_msds(item_code):
	"""Return the latest active MSDS record for a given item_code.

	Usage:
		from gulf_energy.gulf_energy.doctype.msds_register.msds_register import get_active_msds
		msds = get_active_msds("ITEM-001")
	"""
	msds_list = frappe.get_all(
		"MSDS Register",
		filters={
			"item_code": item_code,
			"status": "Active",
			"expiry_date": [">=", today()],
		},
		fields=["name", "version", "valid_from", "expiry_date", "msds_attachment"],
		order_by="valid_from desc",
		limit=1,
	)
	return msds_list[0] if msds_list else None


@frappe.whitelist()
def get_active_msds_for_item(item_code):
	"""Whitelisted wrapper for client-side calls."""
	return get_active_msds(item_code)


def expire_msds_records():
	"""Daily scheduled job: mark all MSDS records past expiry as Expired."""
	expired = frappe.get_all(
		"MSDS Register",
		filters={
			"status": ["in", ["Draft", "Active"]],
			"expiry_date": ["<", today()],
		},
		pluck="name",
	)
	for name in expired:
		frappe.db.set_value("MSDS Register", name, "status", "Expired", update_modified=False)
	if expired:
		frappe.db.commit()
