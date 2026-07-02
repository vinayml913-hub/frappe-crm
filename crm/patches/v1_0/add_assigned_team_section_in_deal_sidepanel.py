import json

import frappe


def execute():
	"""
	Add an 'assigned_team_section' to every existing site's CRM Deal side
	panel layout, following the exact same idempotent insert pattern
	already used by FCRM Settings.add_forecasting_section_in_sidepanel
	(insert right after contacts_section if present, otherwise at the
	very front) so the new section shows up automatically without any
	manual layout editing.

	Marked "editable": False and given no "columns"/generic fields, same
	as contacts_section, because it's rendered by fully custom Vue markup
	(AssignedTeamSection.vue) rather than the generic field-list renderer.
	"""
	if not frappe.db.exists("CRM Fields Layout", "CRM Deal-Side Panel"):
		return

	doc = frappe.get_doc("CRM Fields Layout", "CRM Deal-Side Panel")
	if not doc.layout:
		return

	sections = json.loads(doc.layout)

	if any(section.get("name") == "assigned_team_section" for section in sections):
		return  # already applied - safe to re-run

	new_section = {
		"label": "Assigned Team",
		"name": "assigned_team_section",
		"opened": True,
		"editable": False,
	}

	if sections and sections[0].get("name") == "contacts_section":
		sections = [sections[0], new_section, *sections[1:]]
	else:
		sections = [new_section, *sections]

	doc.layout = json.dumps(sections)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
