# Copyright (c) 2026, Pioneer Business Solutions and contributors
# For license information, please see license.txt

"""
Shared record-ownership permission helpers.

Business rule: a Contact or Organization ("Client") is visible only to
the user who created it, plus System Manager/Administrator. This does
NOT apply to CRM Deal, which intentionally keeps its existing, broader
access model (creator, deal_owner/sales_manager/account_manager/
training_engagement_manager, assignees, and shared users - see
crm.fcrm.doctype.crm_deal.crm_deal).

This module is the single source of truth for the Contact/Organization
rule so both doctypes' has_permission/get_permission_query_conditions
hooks reuse the same logic instead of duplicating it.
"""

import frappe

# Only these roles bypass the "creator only" restriction on Contact/
# Organization entirely.
RECORD_ADMIN_ROLES = ("System Manager",)


def is_record_admin(user=None):
	"""True if `user` (default: current session user) has unrestricted access."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(set(frappe.get_roles(user)) & set(RECORD_ADMIN_ROLES))


def owner_only_has_permission(doc, ptype=None, user=None):
	"""Generic has_permission: admin, or you created it. Nothing else."""
	user = user or frappe.session.user
	if is_record_admin(user):
		return True
	return doc.get("owner") == user


def owner_only_query_conditions(doctype, user=None):
	"""Generic get_permission_query_conditions: admin sees all, everyone
	else is restricted to `owner = user` on the given doctype's table."""
	user = user or frappe.session.user
	if is_record_admin(user):
		return ""
	user_e = frappe.db.escape(user)
	return f"`tab{doctype}`.`owner` = {user_e}"
