import frappe


RENAME_MAP = {
	"Qualification": "Qualified",
	"Demo/Making": "Profile Shared",
	"Proposal/Quotation": "Scoping Call / Evaluation",
}


def execute():
	"""
	Rename CRM Deal Status records so the new labels apply everywhere:
	dropdowns, filters, reports, and every existing CRM Deal that
	currently references the old stage name.

	frappe.rename_doc automatically updates all Link/Dynamic Link
	references (CRM Deal.status, CRM Lead Status equivalents, version
	history, etc.) - so no separate CRM Deal update loop is needed.
	"""
	for old_name, new_name in RENAME_MAP.items():
		if not frappe.db.exists("CRM Deal Status", old_name):
			continue
		if frappe.db.exists("CRM Deal Status", new_name):
			# Target name already exists (e.g. patch re-run after partial
			# failure) - skip to avoid a duplicate/merge conflict.
			continue

		frappe.rename_doc(
			"CRM Deal Status",
			old_name,
			new_name,
			ignore_permissions=True,
			force=True,
		)

		# autoname is field:deal_status, so the field itself must also
		# be updated to match the new document name - rename_doc only
		# renames the document, not this data field.
		frappe.db.set_value("CRM Deal Status", new_name, "deal_status", new_name)

	frappe.db.commit()
	frappe.clear_cache(doctype="CRM Deal Status")
