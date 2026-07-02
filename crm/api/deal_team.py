"""
Deal Assigned Team
====================

Multi-employee assignment on CRM Deal, layered on top of Frappe's
existing native assignment mechanism (frappe.desk.form.assign_to) that
this app already uses for deal_owner (see CRMDeal.assign_agent in
crm_deal.py) and already exposes generically via the AssignTo.vue /
AssignToBody.vue components (frappe.desk.form.assign_to.add +
crm.api.doc.remove_assignments).

This module does NOT reimplement assignment - it adds Deal-specific
business rules (max team size, who's allowed to change the team) on
top of the same ToDo-based mechanism, so assigned employees continue to
see the Deal in their existing "My Open ToDos" / worklist exactly like
any other assignment already does, with zero new visibility plumbing
needed.

Why not just modify crm.api.doc.remove_assignments directly?
That function is generic - used by Leads, Tasks, and anything else with
an AssignTo widget. Adding CRM-Deal-only validation there would risk
changing behaviour for every other doctype. Instead, the frontend calls
these Deal-specific wrappers instead of the generic endpoints directly.
"""

import frappe
from frappe import _
from frappe.desk.form.assign_to import add as assign_to_add

from crm.api.doc import remove_assignments as _remove_assignments

MAX_TEAM_SIZE = 10
MIN_TEAM_SIZE = 1

# Roles allowed to add/remove Deal team members. Matches the roles named
# in the request (Admin / Sales Manager / Solution Manager) plus Sales
# Manager's superset, System Manager - consistent with how admin-level
# access is already defined elsewhere in this app (e.g. revenue.py's
# _is_admin, session.py's CRM_ALLOWED_ROLES).
TEAM_MANAGER_ROLES = {"System Manager", "Sales Manager", "Solution Manager"}


def _can_manage_team():
	roles = set(frappe.get_roles())
	return bool(roles.intersection(TEAM_MANAGER_ROLES))


def _require_team_manager():
	if not _can_manage_team():
		frappe.throw(
			_("Only Admin, Sales Manager, or Solution Manager can modify the Assigned Team."),
			frappe.PermissionError,
		)


def _get_assigned_users(deal_name):
	"""Active (non-cancelled) ToDo assignees for this Deal, enriched with
	display info. Mirrors crm.api.doc.get_assigned_users but scoped to
	CRM Deal and returning the shape the frontend section needs."""
	rows = frappe.get_all(
		"ToDo",
		fields=["allocated_to"],
		filters={
			"reference_type": "CRM Deal",
			"reference_name": deal_name,
			"status": ("!=", "Cancelled"),
		},
		order_by="creation asc",
	)
	users = [r["allocated_to"] for r in rows if r.get("allocated_to")]
	# De-duplicate while preserving order (a user could theoretically have
	# more than one active ToDo against the same document in edge cases).
	seen = set()
	unique_users = []
	for u in users:
		if u not in seen:
			seen.add(u)
			unique_users.append(u)
	return unique_users


@frappe.whitelist()
def get_deal_team(deal_name):
	"""Return the current Assigned Team for a Deal, with display info,
	for the sidebar section to render."""
	if not frappe.db.exists("CRM Deal", deal_name):
		frappe.throw(_("Deal {0} not found").format(deal_name))

	user_ids = _get_assigned_users(deal_name)
	if not user_ids:
		return {"team": [], "can_manage": _can_manage_team(), "max_size": MAX_TEAM_SIZE}

	user_rows = frappe.get_all(
		"User",
		filters={"name": ["in", user_ids]},
		fields=["name", "full_name", "user_image"],
	)
	by_name = {u["name"]: u for u in user_rows}

	team = [
		{
			"name": uid,
			"full_name": by_name.get(uid, {}).get("full_name") or uid,
			"user_image": by_name.get(uid, {}).get("user_image"),
		}
		for uid in user_ids
	]

	return {"team": team, "can_manage": _can_manage_team(), "max_size": MAX_TEAM_SIZE}


@frappe.whitelist()
def add_team_members(deal_name, users):
	"""
	Add one or more users to a Deal's Assigned Team.

	users: JSON string or list of user emails to add.

	Enforces:
	  - caller has a team-manager role (Admin / Sales Manager / Solution Manager)
	  - resulting team size does not exceed MAX_TEAM_SIZE
	Uses the same frappe.desk.form.assign_to.add Frappe core call the
	existing AssignTo widget already uses, so assigned users automatically
	get a ToDo and appear in their normal worklist - no separate
	visibility mechanism needed.
	"""
	_require_team_manager()

	if isinstance(users, str):
		users = frappe.parse_json(users)
	if not isinstance(users, list) or not users:
		frappe.throw(_("At least one user must be provided"))

	if not frappe.db.exists("CRM Deal", deal_name):
		frappe.throw(_("Deal {0} not found").format(deal_name))

	current = _get_assigned_users(deal_name)
	new_users = [u for u in users if u and u not in current]

	if not new_users:
		return get_deal_team(deal_name)

	if len(current) + len(new_users) > MAX_TEAM_SIZE:
		frappe.throw(
			_("A Deal can have at most {0} assigned team members. "
			  "Currently {1}, cannot add {2} more.").format(
				MAX_TEAM_SIZE, len(current), len(new_users)
			)
		)

	try:
		assign_to_add({
			"assign_to": new_users,
			"doctype": "CRM Deal",
			"name": deal_name,
		}, ignore_permissions=True)
	except TypeError:
		# Older/newer Frappe signature difference - same fallback pattern
		# already used in crm_deal.py's assign_agent().
		assign_to_add({
			"assign_to": new_users,
			"doctype": "CRM Deal",
			"name": deal_name,
		})
	except Exception:
		frappe.log_error(title="add_team_members failed", message=frappe.get_traceback())
		frappe.throw(_("Could not add team member(s). Please try again."))

	return get_deal_team(deal_name)


@frappe.whitelist()
def remove_team_member(deal_name, user):
	"""
	Remove a single user from a Deal's Assigned Team.

	Enforces:
	  - caller has a team-manager role
	  - at least MIN_TEAM_SIZE (1) member remains after removal
	Delegates the actual ToDo cancellation to the existing, proven
	crm.api.doc.remove_assignments so behaviour matches exactly what the
	generic AssignTo widget already does elsewhere in the app.
	"""
	_require_team_manager()

	if not frappe.db.exists("CRM Deal", deal_name):
		frappe.throw(_("Deal {0} not found").format(deal_name))

	current = _get_assigned_users(deal_name)

	if user not in current:
		return get_deal_team(deal_name)

	if len(current) <= MIN_TEAM_SIZE:
		frappe.throw(
			_("A Deal must have at least {0} assigned team member. "
			  "Add another member before removing this one.").format(MIN_TEAM_SIZE)
		)

	_remove_assignments("CRM Deal", deal_name, [user], ignore_permissions=True)

	return get_deal_team(deal_name)
