import frappe

from crm.fcrm.doctype.crm_deal.deal_commercial_calculator import (
	get_deal_commercial_calculator_script,
)

SCRIPT_NAME = "Deal Commercial Calculator"


def execute():
	"""
	Installs (or updates, if it already exists) the CRM Form Script that
	live-calculates Proposed/Landing totals and Gross Profit in the
	browser as the user types, mirroring calculate_financials() in
	crm_deal.py. Runs on "Form" view, which covers both the Create Deal
	(Quick Entry) modal and the full Deal form/sidebar - both go through
	the same FieldLayout -> triggerOnChange() mechanism.
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
