# Copyright (c) 2026, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	"""Add custom fields for shipping compliance on Item and Customs Tariff Number."""

	custom_fields = {
		"Customs Tariff Number": [
			dict(
				fieldname="custom_is_hazardous",
				label="Is Hazardous",
				fieldtype="Check",
				insert_after="description",
				description="Flag this HS code as hazardous by default",
			),
			dict(
				fieldname="custom_requires_msds",
				label="Requires MSDS",
				fieldtype="Check",
				insert_after="custom_is_hazardous",
				description="Items with this tariff code require an MSDS document",
			),
			dict(
				fieldname="custom_requires_export_license",
				label="Requires Export License",
				fieldtype="Check",
				insert_after="custom_requires_msds",
				description="Items with this tariff code require an export license",
			),
			dict(
				fieldname="custom_default_imo_class",
				label="Default IMO Class",
				fieldtype="Select",
				options="\nClass 1 - Explosives\nClass 2 - Gases\nClass 3 - Flammable Liquids\nClass 4 - Flammable Solids\nClass 5 - Oxidizing Substances\nClass 6 - Toxic Substances\nClass 7 - Radioactive Material\nClass 8 - Corrosives\nClass 9 - Miscellaneous",
				insert_after="custom_requires_export_license",
				depends_on="eval:doc.custom_is_hazardous",
				description="Default IMO Dangerous Goods class for this tariff code",
			),
		],
		"Item": [
			# --- Hazardous Goods Section ---
			dict(
				fieldname="custom_hazardous_goods_section",
				label="Hazardous Goods & Compliance",
				fieldtype="Section Break",
				insert_after="customs_tariff_number",
				collapsible=1,
			),
			dict(
				fieldname="custom_is_hazardous",
				label="Is Hazardous (DG Cargo)",
				fieldtype="Check",
				insert_after="custom_hazardous_goods_section",
				description="Mark this item as Dangerous Goods",
			),
			dict(
				fieldname="custom_msds_required",
				label="MSDS Required",
				fieldtype="Check",
				insert_after="custom_is_hazardous",
				description="Material Safety Data Sheet is mandatory for this item",
			),
			dict(
				fieldname="custom_un_number",
				label="UN Number",
				fieldtype="Data",
				insert_after="custom_msds_required",
				depends_on="eval:doc.custom_is_hazardous",
				description="United Nations number for hazardous substance identification",
			),
			dict(
				fieldname="custom_imo_class",
				label="IMO Class",
				fieldtype="Select",
				options="\nClass 1 - Explosives\nClass 2 - Gases\nClass 3 - Flammable Liquids\nClass 4 - Flammable Solids\nClass 5 - Oxidizing Substances\nClass 6 - Toxic Substances\nClass 7 - Radioactive Material\nClass 8 - Corrosives\nClass 9 - Miscellaneous",
				insert_after="custom_un_number",
				depends_on="eval:doc.custom_is_hazardous",
			),
			dict(
				fieldname="custom_hazardous_column_break",
				fieldtype="Column Break",
				insert_after="custom_imo_class",
			),
			dict(
				fieldname="custom_packing_group",
				label="Packing Group",
				fieldtype="Select",
				options="\nI\nII\nIII",
				insert_after="custom_hazardous_column_break",
				depends_on="eval:doc.custom_is_hazardous",
				description="UN Packing Group (I=Great danger, II=Medium, III=Minor)",
			),
			dict(
				fieldname="custom_flash_point",
				label="Flash Point (°C)",
				fieldtype="Float",
				insert_after="custom_packing_group",
				depends_on="eval:doc.custom_is_hazardous",
				precision="1",
			),
			dict(
				fieldname="custom_marine_pollutant",
				label="Marine Pollutant",
				fieldtype="Check",
				insert_after="custom_flash_point",
				depends_on="eval:doc.custom_is_hazardous",
			),
			dict(
				fieldname="custom_proper_shipping_name",
				label="Proper Shipping Name",
				fieldtype="Data",
				insert_after="custom_marine_pollutant",
				depends_on="eval:doc.custom_is_hazardous",
				description="Official transport name per IMDG/IATA regulations",
			),
			# --- Export Control Section ---
			dict(
				fieldname="custom_export_control_section",
				label="Export Control",
				fieldtype="Section Break",
				insert_after="custom_proper_shipping_name",
				collapsible=1,
			),
			dict(
				fieldname="custom_export_license_required",
				label="Export License Required",
				fieldtype="Check",
				insert_after="custom_export_control_section",
			),
			dict(
				fieldname="custom_ex_code",
				label="Export Control Code",
				fieldtype="Data",
				insert_after="custom_export_license_required",
				depends_on="eval:doc.custom_export_license_required",
				description="DGFT/Export control classification code",
			),
		],
	}

	create_custom_fields(custom_fields, ignore_validate=True)
