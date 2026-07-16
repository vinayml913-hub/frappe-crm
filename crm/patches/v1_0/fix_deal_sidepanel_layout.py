import json

import frappe


def execute():
	"""
	Recreate the CRM Deal 'Side Panel' fields layout if it's missing
	or its layout JSON is empty. Fixes a blank right-side panel on
	the Deal page caused by a corrupted/deleted CRM Fields Layout record.
	"""
	existing = frappe.db.exists("CRM Fields Layout", {"dt": "CRM Deal", "type": "Side Panel"})

	needs_recreate = True
	if existing:
		layout_value = frappe.db.get_value("CRM Fields Layout", existing, "layout")
		if layout_value:
			needs_recreate = False

	if not needs_recreate:
		return

	if existing:
		frappe.delete_doc("CRM Fields Layout", existing, ignore_permissions=True, force=True)
		frappe.db.commit()

	create_doctype_fields_layout("CRM Deal")
	frappe.db.commit()


def create_doctype_fields_layout(doctype):
	not_allowed_fieldtypes = [
		"Section Break",
		"Column Break",
	]

	fields = frappe.get_meta(doctype).fields
	fields = [field for field in fields if field.fieldtype not in not_allowed_fieldtypes]

	sections = {}
	section_fields = []
	last_section = None

	for field in fields:
		if field.fieldtype == "Tab Break" and last_section:
			sections[last_section]["fields"] = section_fields
			last_section = None
			if field.read_only:
				section_fields = []
				continue
		if field.fieldtype == "Tab Break":
			if field.read_only:
				section_fields = []
				continue
			section_fields = []
			last_section = field.fieldname
			sections[field.fieldname] = {
				"label": field.label,
				"name": field.fieldname,
				"opened": True,
				"fields": [],
			}
			if field.fieldname == "contacts_tab":
				sections[field.fieldname]["editable"] = False
				sections[field.fieldname]["contacts"] = []
		else:
			section_fields.append(field.fieldname)

	if last_section:
		sections[last_section]["fields"] = section_fields

	section_fields = []
	for section in sections:
		if section == "contacts_tab":
			sections[section]["name"] = "contacts_section"
			sections[section].pop("fields", None)
		section_fields.append(sections[section])

	frappe.get_doc(
		{
			"doctype": "CRM Fields Layout",
			"dt": doctype,
			"type": "Side Panel",
			"layout": json.dumps(section_fields),
		}
	).insert(ignore_permissions=True)

	return section_fields
