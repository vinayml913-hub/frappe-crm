import frappe

from crm.install import add_default_fields_layout


def execute():
	"""
	The Deal's "Trainer Details" section only showed the Trainer Link
	field (CRM-TRAINER-2026-XXXXX), not the trainer's actual name, since
	the "CRM Deal-Quick Entry" and "CRM Deal-Data Fields" fields layouts
	were created before the new "trainer_name" fetched field existed.

	Force-recreate just those two layouts so "trainer_name" (auto-fetched
	from CRM Trainer.trainer_name whenever "trainer" is set) shows up
	right next to Trainer. The Side Panel layout doesn't show Trainer
	Details, so it's left untouched.
	"""
	for layout_name in ("CRM Deal-Quick Entry", "CRM Deal-Data Fields"):
		if frappe.db.exists("CRM Fields Layout", layout_name):
			frappe.delete_doc("CRM Fields Layout", layout_name, ignore_permissions=True)

	add_default_fields_layout(force=False)
