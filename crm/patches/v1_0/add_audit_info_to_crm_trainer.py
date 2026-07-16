import frappe


def execute():
	"""
	Expose audit information (Created On / Created By / Last Updated On /
	Last Updated By) on the CRM Trainer doctype.

	`creation`, `owner`, `modified` and `modified_by` are standard Frappe
	columns that already exist on every doctype table (including
	`tabCRM Trainer`) and have been populated automatically since the very
	first trainer record was created. This patch does not add any new
	database column and does not modify any existing data - it simply
	reloads the doctype so the newly declared fields (which surface these
	already-existing columns in the UI/API) are picked up on sites that
	migrated before this change shipped.
	"""
	if not frappe.db.exists("DocType", "CRM Trainer"):
		return

	frappe.reload_doctype("CRM Trainer", force=True)
