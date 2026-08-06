import frappe

from crm.install import add_default_fields_layout


def execute():
	"""
	Rebuilds the "CRM Deal-Quick Entry" (Create Deal) layout to match the
	new Training Details / Commercial (Proposed vs Landing) / Team / Notes
	structure. Existing sites already have an old layout row saved, so the
	normal installer (which skips if the record exists) won't touch it -
	this patch force-recreates just that one record.
	"""
	if frappe.db.exists("CRM Fields Layout", "CRM Deal-Quick Entry"):
		frappe.delete_doc("CRM Fields Layout", "CRM Deal-Quick Entry", ignore_permissions=True)

	add_default_fields_layout(force=False)
