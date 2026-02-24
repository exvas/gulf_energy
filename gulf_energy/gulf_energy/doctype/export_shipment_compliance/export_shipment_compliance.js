// Copyright (c) 2026, sammish and contributors
// For license information, please see license.txt

frappe.ui.form.on("Export Shipment Compliance", {
	refresh: function (frm) {
		// Color indicator for compliance status
		if (frm.doc.compliance_status === "Complete") {
			frm.dashboard.set_headline(
				__("Compliance Status: Complete"),
				"green"
			);
		} else if (frm.doc.compliance_status === "Partial") {
			frm.dashboard.set_headline(
				__("Compliance Status: Partial"),
				"orange"
			);
		} else if (frm.doc.compliance_status === "Pending") {
			frm.dashboard.set_headline(
				__("Compliance Status: Pending"),
				"red"
			);
		}

		// Add action buttons only if not submitted/cancelled
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(
				__("Auto-populate Checklist"),
				function () {
					frappe.call({
						method: "gulf_energy.gulf_energy.doctype.export_shipment_compliance.export_shipment_compliance.auto_populate_checklist",
						args: { docname: frm.doc.name },
						freeze: true,
						freeze_message: __("Generating checklist..."),
						callback: function () {
							frm.reload_doc();
							frappe.show_alert({
								message: __("Compliance checklist generated"),
								indicator: "green",
							});
						},
					});
				},
				__("Compliance")
			);

			frm.add_custom_button(
				__("Validate Compliance"),
				function () {
					frappe.call({
						method: "gulf_energy.gulf_energy.doctype.export_shipment_compliance.export_shipment_compliance.validate_compliance",
						args: { docname: frm.doc.name },
						freeze: true,
						freeze_message: __("Validating compliance..."),
						callback: function (r) {
							frm.reload_doc();
							if (r.message) {
								frappe.show_alert({
									message: r.message.message,
									indicator:
										r.message.compliance_status === "Complete"
											? "green"
											: "orange",
								});
							}
						},
					});
				},
				__("Compliance")
			);
		}

		// Filter sales_order and delivery_note by company
		frm.set_query("sales_order", function () {
			return {
				filters: {
					company: frm.doc.company,
					docstatus: 1,
				},
			};
		});

		frm.set_query("delivery_note", function () {
			return {
				filters: {
					company: frm.doc.company,
					docstatus: 1,
				},
			};
		});
	},

	shipment_type: function (frm) {
		// Show/hide B/L fields based on shipment type
		var is_sea = frm.doc.shipment_type === "Sea";
		frm.toggle_display("bl_type", is_sea);
		frm.toggle_display("vessel_name", is_sea);
		frm.toggle_display("voyage_no", is_sea);
		frm.toggle_display("country_of_flag", is_sea);
	},
});

// Child table events for Shipment Container
frappe.ui.form.on("Shipment Container", {
	gross_weight: function (frm) {
		calculate_weight_totals(frm);
	},

	net_weight: function (frm) {
		calculate_weight_totals(frm);
	},

	containers_remove: function (frm) {
		calculate_weight_totals(frm);
	},
});

// Child table events for Shipping Document
frappe.ui.form.on("Shipping Document", {
	attachment: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "is_uploaded", row.attachment ? 1 : 0);
	},
});

function calculate_weight_totals(frm) {
	var total_gross = 0;
	var total_net = 0;

	(frm.doc.containers || []).forEach(function (row) {
		total_gross += flt(row.gross_weight);
		total_net += flt(row.net_weight);
	});

	frm.set_value("total_containers", (frm.doc.containers || []).length);
	frm.set_value("total_gross_weight", total_gross);
	frm.set_value("total_net_weight", total_net);
}
