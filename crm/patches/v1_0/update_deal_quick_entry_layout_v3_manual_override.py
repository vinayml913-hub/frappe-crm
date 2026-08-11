import frappe

from crm.install import add_default_fields_layout


def execute():
	"""
	Adds the "Enter Proposed/Landing Total Manually" override checkboxes
	next to their respective totals in the Create Deal (Quick Entry)
	layout. Site already ran update_deal_quick_entry_layout_v2_commercial,
	so that record exists and the normal installer would skip it again -
	force-recreate just this one record, same as that earlier patch did.
	"""
	if frappe.db.exists("CRM Fields Layout", "CRM Deal-Quick Entry"):
		frappe.delete_doc("CRM Fields Layout", "CRM Deal-Quick Entry", ignore_permissions=True)

	add_default_fields_layout(force=False)
