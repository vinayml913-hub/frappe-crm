import frappe

from crm.install import add_default_fields_layout


def execute():
	"""
	"CRM Deal-Data Fields" (the main "Data" tab on an open Deal) and
	"CRM Deal-Side Panel" (the right-hand summary sidebar) were never
	updated when the Commercial model changed - only the Quick Entry
	(Create Deal) layout was. Both still referenced the OLD field
	structure, which is why:
	  - the Data tab was missing the "Enter Total Manually" override
	    checkboxes entirely, so Proposed/Landing Total stayed locked
	    there even after they'd been unlocked in Create Deal
	  - either layout may still reference now-deleted fields
	    (account_manager, trainer_commercial, lab_expense, etc.), which
	    would error once those columns are actually gone after migrate

	This force-recreates both records with the new field structure.
	"""
	for layout_name in ("CRM Deal-Data Fields", "CRM Deal-Side Panel"):
		if frappe.db.exists("CRM Fields Layout", layout_name):
			frappe.delete_doc("CRM Fields Layout", layout_name, ignore_permissions=True)

	add_default_fields_layout(force=False)
