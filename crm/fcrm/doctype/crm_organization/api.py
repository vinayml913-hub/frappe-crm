# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def link_contact(organization: str, contact: str):
	"""Associate an existing Contact with a CRM Organization.

	This is used by the "Link Existing Contact" option in the Client
	(CRM Organization) details page. It simply points the Contact's
	`company_name` to the given organization, mirroring how the
	Contacts tab on the Organization page already filters contacts
	(`company_name == organization`).
	"""
	if not frappe.has_permission("CRM Organization", "write", organization):
		frappe.throw(
			_("Not allowed to link contact to this Client"), frappe.PermissionError
		)

	if not frappe.has_permission("Contact", "write", contact):
		frappe.throw(_("Not allowed to update this Contact"), frappe.PermissionError)

	if not frappe.db.exists("CRM Organization", organization):
		frappe.throw(_("Client {0} not found").format(organization))

	contact_doc = frappe.get_doc("Contact", contact)

	if contact_doc.company_name == organization:
		frappe.throw(_("Contact is already linked to this Client"))

	contact_doc.company_name = organization
	contact_doc.save()

	return contact_doc.name  
