// Copyright (c) 2026, sammish and contributors
// Shipping Compliance: Auto-fetch hazardous flags from Customs Tariff Number

frappe.ui.form.on("Item", {
	customs_tariff_number: function (frm) {
		if (frm.doc.customs_tariff_number) {
			frappe.db.get_value(
				"Customs Tariff Number",
				frm.doc.customs_tariff_number,
				[
					"custom_is_hazardous",
					"custom_requires_msds",
					"custom_requires_export_license",
					"custom_default_imo_class",
				],
				function (r) {
					if (r) {
						if (r.custom_is_hazardous) {
							frm.set_value("custom_is_hazardous", r.custom_is_hazardous);
						}
						if (r.custom_requires_msds) {
							frm.set_value("custom_msds_required", r.custom_requires_msds);
						}
						if (r.custom_requires_export_license) {
							frm.set_value(
								"custom_export_license_required",
								r.custom_requires_export_license
							);
						}
						if (r.custom_default_imo_class) {
							frm.set_value("custom_imo_class", r.custom_default_imo_class);
						}

						if (r.custom_is_hazardous || r.custom_requires_msds) {
							frappe.show_alert({
								message: __(
									"Compliance flags auto-populated from HS Code {0}",
									[frm.doc.customs_tariff_number]
								),
								indicator: "blue",
							});
						}
					}
				}
			);
		} else {
			// Tariff cleared: reset compliance fields
			frm.set_value("custom_is_hazardous", 0);
			frm.set_value("custom_msds_required", 0);
			frm.set_value("custom_export_license_required", 0);
			frm.set_value("custom_imo_class", "");
		}
	},
});
