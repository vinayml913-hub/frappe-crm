import frappe


def execute():
	"""
	Add the new `alternate_phone` and `commercial_type` fields to the
	CRM Trainer doctype.

	`frappe.reload_doctype` syncs the table schema to match the updated
	crm_trainer.json - it ADDs the two new columns (both nullable, no
	default that could overwrite anything except `commercial_type`,
	which defaults new/blank rows to "Per Day" going forward only).
	Existing trainer records are left completely untouched: their
	existing columns and values are not modified, and the two new
	columns will simply be NULL/empty until edited.
	"""
	if not frappe.db.exists("DocType", "CRM Trainer"):
		return

	frappe.reload_doctype("CRM Trainer", force=True)
