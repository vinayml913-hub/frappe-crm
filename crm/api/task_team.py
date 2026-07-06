"""
Task Assigned Team (multi-person Task assignment)
====================================================

Mirrors crm/api/deal_team.py's design and rules exactly (same
TEAM_MANAGER_ROLES, same MAX/MIN team size, same creator-exception
security model for assign_team_on_create) but adapted for CRM Task's
different underlying architecture:

CRM Task, unlike CRM Deal, does NOT already use Frappe's ToDo-based
multi-assignment - it has a single `assigned_to` Link field, tightly
coupled to a ToDo via CRMTask.assign_to()/unassign_from_previous_user()
in crm_task.py (assign/reassign on save, single user only). That field
is read directly (as a single value) in ~10 other frontend files and
~10 other backend files (lists, filters, notifications) - changing its
type would be a wide, risky breaking change, so it is NOT modified here.

Instead, this module adds genuine multi-person assignment via the same
ToDo mechanism CRM Deal already uses, and keeps `assigned_to` as a
backward-compatible mirror of the "primary" team member (team[0], in
assignment order) so every existing consumer of `assigned_to` keeps
working unchanged. The mirror is updated ONLY through this module's own
functions, specifically to avoid fighting crm_task.py's own
assign/reassign side effects - see _sync_primary_assignee() below for
exactly how that hand-off works.

Notifications: frappe.desk.form.assign_to.add() creates a ToDo, and
crm.api.todo.after_insert (already registered in hooks.py for CRM Task)
automatically notifies the newly assigned user - no extra notification
code needed here, confirmed against the existing hook.
"""

import frappe
from frappe import _
from frappe.desk.form.assign_to import add as assign_to_add

from crm.api.doc import remove_assignments as _remove_assignments

MAX_TEAM_SIZE = 10
MIN_TEAM_SIZE = 1

TEAM_MANAGER_ROLES = {"System Manager", "Sales Manager", "Solution Manager"}


def _can_manage_team():
	roles = set(frappe.get_roles())
	return bool(roles.intersection(TEAM_MANAGER_ROLES))


def _require_team_manager():
	if not _can_manage_team():
		frappe.throw(
			_("Only Admin, Sales Manager, or Solution Manager can modify the Task's assigned team."),
			frappe.PermissionError,
		)


def _get_assigned_users(task_name):
	"""Active (non-cancelled) ToDo assignees for this Task, in the order
	they were assigned - team[0] is treated as the 'primary' assignee
	and mirrored into the legacy assigned_to field."""
	rows = frappe.get_all(
		"ToDo",
		fields=["allocated_to"],
		filters={
			"reference_type": "CRM Task",
			"reference_name": task_name,
			"status": ("!=", "Cancelled"),
		},
		order_by="creation asc",
	)
	users = [r["allocated_to"] for r in rows if r.get("allocated_to")]
	seen = set()
	unique_users = []
	for u in users:
		if u not in seen:
			seen.add(u)
			unique_users.append(u)
	return unique_users


def _sync_primary_assignee(task_name, new_primary):
	"""
	Update CRM Task.assigned_to to new_primary via doc.save(), so
	crm_task.py's OWN validate()/assign_to()/unassign_from_previous_user()
	logic runs exactly as it already does for any normal assigned_to
	change - reassigning that one ToDo correctly, with zero duplicate
	logic here. This function is the ONLY place in this module that ever
	touches assigned_to directly.

	Called with new_primary=None when the team becomes empty (should
	only happen transiently - MIN_TEAM_SIZE prevents removal down to
	zero via the public API, this is a defensive fallback).
	"""
	doc = frappe.get_doc("CRM Task", task_name)
	if doc.assigned_to == new_primary:
		return  # no-op, already in sync
	doc.assigned_to = new_primary
	# NOTE: this doc.save() will cause crm_task.py's own validate() ->
	# assign_to() to call frappe.desk.form.assign_to.add() again for
	# new_primary, even though this module may have just assigned them
	# moments earlier via its own direct call. This is expected and safe
	# - Frappe core's assign_to.add() already skips creating a duplicate
	# ToDo when the user is already actively assigned to the document
	# (the same behaviour every existing single-assignee Task save in
	# this app already relies on today, unrelated to this change).
	doc.save(ignore_permissions=True)
	frappe.db.commit()


@frappe.whitelist()
def get_task_team(task_name):
	"""Current Assigned Team for a Task, with display info."""
	if not frappe.db.exists("CRM Task", task_name):
		frappe.throw(_("Task {0} not found").format(task_name))

	user_ids = _get_assigned_users(task_name)
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
def add_team_members(task_name, users):
	"""
	Add one or more users to a Task's Assigned Team. Manager-only (System
	Manager / Sales Manager / Solution Manager) for an EXISTING task -
	see assign_team_on_create() for the separate creator exception used
	right after a new task is inserted.
	"""
	_require_team_manager()

	if isinstance(users, str):
		users = frappe.parse_json(users)
	if not isinstance(users, list) or not users:
		frappe.throw(_("At least one user must be provided"))

	if not frappe.db.exists("CRM Task", task_name):
		frappe.throw(_("Task {0} not found").format(task_name))

	current = _get_assigned_users(task_name)
	new_users = [u for u in users if u and u not in current]

	if not new_users:
		return get_task_team(task_name)

	if len(current) + len(new_users) > MAX_TEAM_SIZE:
		frappe.throw(
			_("A Task can have at most {0} assigned team members. "
			  "Currently {1}, cannot add {2} more.").format(
				MAX_TEAM_SIZE, len(current), len(new_users)
			)
		)

	was_empty = not current

	try:
		assign_to_add({
			"assign_to": new_users,
			"doctype": "CRM Task",
			"name": task_name,
		}, ignore_permissions=True)
	except TypeError:
		assign_to_add({
			"assign_to": new_users,
			"doctype": "CRM Task",
			"name": task_name,
		})
	except Exception:
		frappe.log_error(title="Task add_team_members failed", message=frappe.get_traceback())
		frappe.throw(_("Could not add team member(s). Please try again."))

	if was_empty:
		# The team had no primary yet - the first newly-added user becomes
		# it, syncing the legacy assigned_to field for backward compat.
		_sync_primary_assignee(task_name, new_users[0])

	return get_task_team(task_name)


@frappe.whitelist()
def remove_team_member(task_name, user):
	"""
	Remove a single user from a Task's Assigned Team. Manager-only.
	Enforces the MIN_TEAM_SIZE floor (a Task must always keep at least
	one assignee).

	If the removed user is the current primary (mirrored into
	assigned_to), the new primary is promoted FIRST via
	_sync_primary_assignee() - which lets crm_task.py's own
	unassign_from_previous_user() cancel the old primary's ToDo as part
	of that normal field-change flow, so this function does NOT also
	call _remove_assignments for that specific user (that would be
	redundant/could race with the controller's own cleanup). For any
	non-primary removal, _remove_assignments is called directly since
	crm_task.py's field-driven logic never touches those ToDos anyway.
	"""
	_require_team_manager()

	if not frappe.db.exists("CRM Task", task_name):
		frappe.throw(_("Task {0} not found").format(task_name))

	current = _get_assigned_users(task_name)

	if user not in current:
		return get_task_team(task_name)

	if len(current) <= MIN_TEAM_SIZE:
		frappe.throw(
			_("A Task must have at least {0} assigned team member. "
			  "Add another member before removing this one.").format(MIN_TEAM_SIZE)
		)

	current_primary = frappe.db.get_value("CRM Task", task_name, "assigned_to")

	if user == current_primary:
		remaining = [u for u in current if u != user]
		new_primary = remaining[0] if remaining else None
		_sync_primary_assignee(task_name, new_primary)
	else:
		_remove_assignments("CRM Task", task_name, [user], ignore_permissions=True)

	return get_task_team(task_name)


@frappe.whitelist()
def assign_team_on_create(task_name, users):
	"""
	One-time, creator-only team assignment for a freshly created Task.
	Same three-condition security boundary as
	crm.api.deal_team.assign_team_on_create - see that function's
	docstring for the full rationale. Repeated here rather than shared
	as a generic helper to keep each doctype's rules independently
	auditable and to avoid a premature abstraction across two modules
	that may diverge later.
	"""
	if not frappe.db.exists("CRM Task", task_name):
		frappe.throw(_("Task {0} not found").format(task_name))

	if isinstance(users, str):
		users = frappe.parse_json(users)
	if not isinstance(users, list) or not users:
		frappe.throw(_("At least one user must be provided"))

	task_creator = frappe.db.get_value("CRM Task", task_name, "owner")
	if task_creator != frappe.session.user:
		frappe.throw(
			_("Only the person who created this Task can set its initial team."),
			frappe.PermissionError,
		)

	if not frappe.has_permission("CRM Task", "write", task_name):
		frappe.throw(_("You do not have permission to modify this Task."), frappe.PermissionError)

	current = _get_assigned_users(task_name)
	if current:
		frappe.throw(
			_("This Task already has an assigned team. "
			  "Further changes must be made by an Admin, Sales Manager, or Solution Manager."),
			frappe.PermissionError,
		)

	users = list(dict.fromkeys(users))
	if len(users) > MAX_TEAM_SIZE:
		frappe.throw(
			_("A Task can have at most {0} assigned team members. You selected {1}.").format(
				MAX_TEAM_SIZE, len(users)
			)
		)

	try:
		assign_to_add({
			"assign_to": users,
			"doctype": "CRM Task",
			"name": task_name,
		}, ignore_permissions=True)
	except TypeError:
		assign_to_add({
			"assign_to": users,
			"doctype": "CRM Task",
			"name": task_name,
		})
	except Exception:
		frappe.log_error(title="Task assign_team_on_create failed", message=frappe.get_traceback())
		frappe.throw(_("Could not assign team member(s). Please try again."))

	_sync_primary_assignee(task_name, users[0])

	return get_task_team(task_name)
