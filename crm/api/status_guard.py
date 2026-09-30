import frappe
from frappe import _

# Users whose highest CRM role is one of these cannot change status.
# Anyone who also holds an exempt role is allowed.
RESTRICTED_ROLES = {"Solution Manager"}
EXEMPT_ROLES = {"System Manager", "Sales Manager", "Sales User"}


def validate_status_change(doc, method=None):
	if doc.is_new() or frappe.flags.in_patch or frappe.flags.in_install:
		return
	if not doc.has_value_changed("status"):
		return

	roles = set(frappe.get_roles())
	if roles & RESTRICTED_ROLES and not roles & EXEMPT_ROLES:
		frappe.throw(
			_("You are not allowed to change the status."),
			frappe.PermissionError,
		)
