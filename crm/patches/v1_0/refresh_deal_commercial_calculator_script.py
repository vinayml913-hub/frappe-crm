import frappe

from crm.fcrm.doctype.crm_deal.deal_commercial_calculator import (
	get_deal_commercial_calculator_script,
)

SCRIPT_NAME = "Deal Commercial Calculator"


def execute():
	"""
	The original install_deal_commercial_calculator_script patch already
	ran once (5 days before the field-name mismatch was caught and fixed
	in deal_commercial_calculator.py). Patches never re-run automatically,
	so the DB record was left holding the stale/incorrect script.

	This patch force-overwrites it with the current script via
	frappe.db.set_value - a direct DB write that bypasses
	CRMFormScript.validate()'s "Is Standard" edit lock, since that lock
	only applies to edits made through the Desk UI/Document API, not to
	patches (frappe.flags.in_patch is set here).
	"""
	script = get_deal_commercial_calculator_script()

	if frappe.db.exists("CRM Form Script", SCRIPT_NAME):
		frappe.db.set_value("CRM Form Script", SCRIPT_NAME, "script", script)
		return

	frappe.get_doc(
		{
			"doctype": "CRM Form Script",
			"name": SCRIPT_NAME,
			"dt": "CRM Deal",
			"view": "Form",
			"script": script,
			"enabled": 1,
			"is_standard": 1,
		}
	).insert(ignore_permissions=True)
