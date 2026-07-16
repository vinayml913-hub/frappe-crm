from frappe.contacts.doctype.contact.contact import Contact

from crm.utils.permissions import owner_only_has_permission, owner_only_query_conditions

# Record-level access to Contact is strict "creator only", same rule as
# CRM Deal/CRM Organization - see crm.utils.permissions. Only System
# Manager/Administrator bypass this. Registered in hooks.py under
# permission_query_conditions / has_permission (Contact is a core Frappe
# doctype, not owned by this app, so it's customized here rather than in
# its doctype json).
#
# Caveat: a Contact created by one user but linked to another user's Deal
# will no longer be visible to that second user under this rule. If
# Contacts should instead follow "visible if linked to a Deal you can
# see", that needs a different (reference-aware) check - flag this with
# the business before relying on it.


def has_permission(doc, ptype=None, user=None):
	"""A Contact is visible only to the user who created it, or to a
	System Manager/Administrator."""
	return owner_only_has_permission(doc, ptype=ptype, user=user)


def get_permission_query_conditions(user=None):
	"""List/kanban/report view counterpart to has_permission() above."""
	return owner_only_query_conditions("Contact", user=user)


class CustomContact(Contact):
	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Name",
				"type": "Data",
				"key": "full_name",
				"width": "17rem",
			},
			{
				"label": "Email",
				"type": "Data",
				"key": "email_id",
				"width": "12rem",
			},
			{
				"label": "Phone",
				"type": "Data",
				"key": "mobile_no",
				"width": "12rem",
			},
			{
				"label": "Organization",
				"type": "Data",
				"key": "company_name",
				"width": "12rem",
			},
			{
				"label": "Last Modified",
				"type": "Datetime",
				"key": "modified",
				"width": "8rem",
			},
		]
		rows = [
			"name",
			"full_name",
			"company_name",
			"email_id",
			"mobile_no",
			"modified",
			"image",
		]
		return {"columns": columns, "rows": rows}
