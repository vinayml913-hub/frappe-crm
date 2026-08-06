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
from crm.api.todo import notify_assigned_user

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


def _notify_new_team_members(deal_name, new_users):
	"""
	Explicitly guarantee a notification is sent to every newly-assigned
	user, by calling the SAME notify_assigned_user() function
	crm.api.todo.after_insert already uses for the existing single-agent
	assignment flow (crm_deal.py's assign_agent) - reusing its message
	formatting and CRM Notification creation logic rather than
	duplicating it.

	Why this exists as an explicit call, rather than relying only on the
	ToDo `after_insert` doc_event firing automatically for each user when
	assign_to_add() is called with a LIST of multiple users in one
	request: that hook chain is not independently verifiable in this
	environment (no Frappe core source available to confirm per-ToDo
	hook firing during a batched multi-user assign call), so this
	function makes notification delivery a first-class, guaranteed part
	of THIS module's own code instead of an assumed side effect.
	Calling notify_assigned_user() twice for the same user (once via the
	hook, once via this explicit call) is safe and produces no duplicate
	notification - see notify_user()'s own frappe.db.exists() check in
	crm_notification.py, which already de-duplicates identical
	(from_user, to_user, message, ...) combinations.
	"""
	for user in new_users:
		try:
			notify_assigned_user(frappe._dict({
				"reference_type": "CRM Deal",
				"reference_name": deal_name,
				"allocated_to": user,
			}))
		except Exception:
			# Notification failure should never block the actual
			# assignment from succeeding - log and continue.
			frappe.log_error(
				title="Deal team assignment notification failed",
				message=frappe.get_traceback(),
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

	_notify_new_team_members(deal_name, new_users)

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


# ─────────────────────────────────────────────────────────────────────────
#  Creation-time exception
# ─────────────────────────────────────────────────────────────────────────
#
# Requirement: "whoever creates the deal can assign that deal to 1-10
# employees" - i.e. the CREATOR of a new Deal may set its initial team,
# even if they don't hold a team-manager role (System Manager / Sales
# Manager / Solution Manager). Once the deal exists with a team, all
# FURTHER changes go back through add_team_members/remove_team_member
# above, which remain manager-only.
#
# This can't be enforced by "was this call made within N seconds of
# insert" (too fragile/spoofable), so instead it's bounded by three
# separate, server-verifiable conditions - ALL must hold:
#   1. The calling user is the Deal's `owner` (Frappe's built-in
#      "who created this record" field - distinct from the custom
#      `deal_owner` field), i.e. they are the actual creator.
#   2. The Deal currently has ZERO assigned team members - this makes
#      the exception genuinely single-use: once a team exists (even a
#      team of one), this function refuses and the caller must use the
#      manager-gated endpoints instead.
#   3. The calling user has standard Frappe "write" permission on this
#      Deal (normal doctype permission - already true for any Sales
#      User per the existing CRM Deal permission rows).
# This means a Sales User can set the team once, immediately after
# creating their own deal, and never again - closing the gap a
# time-based check would leave open.

@frappe.whitelist()
def assign_team_on_create(deal_name, users):
	"""
	One-time, creator-only team assignment for a freshly created Deal.
	See the module-level comment above for the exact security boundary.
	"""
	if not frappe.db.exists("CRM Deal", deal_name):
		frappe.throw(_("Deal {0} not found").format(deal_name))

	if isinstance(users, str):
		users = frappe.parse_json(users)
	if not isinstance(users, list) or not users:
		frappe.throw(_("At least one user must be provided"))

	deal_creator = frappe.db.get_value("CRM Deal", deal_name, "owner")
	if deal_creator != frappe.session.user:
		frappe.throw(
			_("Only the person who created this Deal can set its initial team."),
			frappe.PermissionError,
		)

	if not frappe.has_permission("CRM Deal", "write", deal_name):
		frappe.throw(_("You do not have permission to modify this Deal."), frappe.PermissionError)

	# `current` would incorrectly include deal_owner/sales_manager/
	# solution_managers/training_engagement_manager here - those fields
	# already auto-assign (and notify) whoever they're set to, as part
	# of the same insert() that just created this Deal, which happens
	# BEFORE this separate follow-up request runs. Excluding them from
	# this check means the creator's one-time "Assign To" addition still
	# goes through on a freshly created Deal; the guard still correctly
	# blocks a second, later call (e.g. someone genuinely added via this
	# same endpoint before) since those users aren't excluded.
	# Solution Manager is now a multi-select child table (solution_managers),
	# not a plain field, so it's pulled separately rather than via the
	# single get_value() call below.
	auto_assigned_via_fields = {
		value
		for value in frappe.db.get_value(
			"CRM Deal", deal_name,
			["deal_owner", "sales_manager", "training_engagement_manager"],
			as_dict=True,
		).values()
		if value
	}
	auto_assigned_via_fields.update(
		frappe.db.get_all(
			"CRM Deal Solution Manager",
			filters={"parent": deal_name, "parenttype": "CRM Deal"},
			pluck="user",
		)
	)
	current = [u for u in _get_assigned_users(deal_name) if u not in auto_assigned_via_fields]
	if current:
		frappe.throw(
			_("This Deal already has an assigned team. "
			  "Further changes must be made by an Admin, Sales Manager, or Solution Manager."),
			frappe.PermissionError,
		)

	users = list(dict.fromkeys(users))  # de-duplicate, preserve order
	if len(users) > MAX_TEAM_SIZE:
		frappe.throw(
			_("A Deal can have at most {0} assigned team members. You selected {1}.").format(
				MAX_TEAM_SIZE, len(users)
			)
		)

	try:
		assign_to_add({
			"assign_to": users,
			"doctype": "CRM Deal",
			"name": deal_name,
		}, ignore_permissions=True)
	except TypeError:
		assign_to_add({
			"assign_to": users,
			"doctype": "CRM Deal",
			"name": deal_name,
		})
	except Exception:
		frappe.log_error(title="assign_team_on_create failed", message=frappe.get_traceback())
		frappe.throw(_("Could not assign team member(s). Please try again."))

	_notify_new_team_members(deal_name, users)

	return get_deal_team(deal_name)
