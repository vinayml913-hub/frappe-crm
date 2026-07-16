import json
import frappe


def execute():
	"""Update CRM Deal Quick Entry layout to include PBS Deal Details fields"""

	layout = [
		{
			"name": "organization_section",
			"hidden": True,
			"editable": False,
			"columns": [
				{"name": "column_GpMP", "fields": ["organization"]},
				{"name": "column_FPTn", "fields": []}
			]
		},
		{
			"name": "organization_details_section",
			"editable": False,
			"columns": [
				{"name": "column_S3tQ", "fields": ["organization_name", "territory"]},
				{"name": "column_KqV1", "fields": ["website", "annual_revenue"]},
				{"name": "column_1r67", "fields": ["no_of_employees", "industry"]}
			]
		},
		{
			"name": "contact_section",
			"hidden": True,
			"editable": False,
			"columns": [
				{"name": "column_CeXr", "fields": ["contact"]},
				{"name": "column_yHbk", "fields": []}
			]
		},
		{
			"name": "contact_details_section",
			"editable": False,
			"columns": [
				{"name": "column_ZTWr", "fields": ["salutation", "email"]},
				{"name": "column_tabr", "fields": ["first_name", "mobile_no"]},
				{"name": "column_Qjdx", "fields": ["last_name", "gender"]}
			]
		},
		{
			"name": "deal_section",
			"label": "Deal Details",
			"columns": [
				{"name": "column_mdps", "fields": ["status", "deal_name", "expected_close_date"]},
				{"name": "column_H40H", "fields": ["deal_owner", "stage", "amount"]}
			]
		},
		{
			"name": "pbs_financials_section",
			"label": "Financials",
			"columns": [
				{"name": "column_fin1", "fields": ["expense", "lab_required", "training_required"]},
				{"name": "column_fin2", "fields": ["lead_source"]}
			]
		},
		{
			"name": "pbs_team_section",
			"label": "Team",
			"columns": [
				{"name": "column_team1", "fields": ["sales_manager", "account_manager"]},
				{"name": "column_team2", "fields": ["training_engagement_manager"]}
			]
		}
	]

	if frappe.db.exists("CRM Fields Layout", "CRM Deal-Quick Entry"):
		frappe.db.set_value(
			"CRM Fields Layout",
			"CRM Deal-Quick Entry",
			"layout",
			json.dumps(layout)
		)
		frappe.db.commit()
		print("✅ CRM Deal Quick Entry layout updated with PBS fields")
	else:
		doc = frappe.new_doc("CRM Fields Layout")
		doc.name = "CRM Deal-Quick Entry"
		doc.type = "Quick Entry"
		doc.dt = "CRM Deal"
		doc.layout = json.dumps(layout)
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
		print("✅ CRM Deal Quick Entry layout created with PBS fields")