import json

import frappe
from crm.api.session import get_session_role_flags

# Audit fields are system-managed (set automatically by Frappe on
# insert/save based on the logged-in session user) and must never be
# accepted from client input.
AUDIT_FIELDS = ("owner", "creation", "modified", "modified_by")


def _strip_audit_fields(trainer: dict) -> dict:
	for field in AUDIT_FIELDS:
		trainer.pop(field, None)
	return trainer


def _attach_audit_info(row: dict, user_cache: dict | None = None) -> dict:
	"""Enrich a trainer dict with human-readable creator/updater info.

	Adds `owner_name` / `owner_email` for who created the record and
	`modified_by_name` / `modified_by_email` for who last updated it,
	falling back gracefully (None) so the frontend can render "N/A"
	instead of erroring out on older/incomplete records.

	`user_cache` can be passed in by callers enriching multiple rows
	(e.g. a list view) to avoid re-fetching the same user repeatedly.
	"""
	if user_cache is None:
		user_cache = {}

	def _user_info(user_id):
		if not user_id:
			return None, None
		if user_id not in user_cache:
			user_cache[user_id] = frappe.db.get_value(
				"User", user_id, ["full_name", "email"]
			) or (None, None)
		return user_cache[user_id]

	full_name, email = _user_info(row.get("owner"))
	row["owner_name"] = full_name or row.get("owner")
	row["owner_email"] = email

	full_name, email = _user_info(row.get("modified_by"))
	row["modified_by_name"] = full_name or row.get("modified_by")
	row["modified_by_email"] = email

	return row


@frappe.whitelist()
def get_trainers(
	filters: str | None = None,
	order_by: str = "modified desc",
	page_length: int = 20,
	page: int = 1,
	search: str | None = None,
) -> dict:
	get_session_role_flags()

	_filters = {}
	if search:
		_filters["trainer_name"] = ["like", f"%{search}%"]

	if filters:
		if isinstance(filters, str):
			filters = json.loads(filters)
		_filters.update(filters)

	offset = (page - 1) * page_length

	trainers = frappe.get_all(
		"CRM Trainer",
		filters=_filters,
		fields=[
			"name",
			"trainer_name",
			"phone",
			"email",
			"linkedin_profile",
			"location",
			"technology_expert_in",
			"skill_level",
			"experience",
			"availability",
			"status",
			"commercial",
			"company",
			"remarks",
			"modified",
			"modified_by",
			"creation",
			"owner",
		],
		order_by=order_by,
		limit=page_length,
		start=offset,
		ignore_permissions=True,
	)

	# Enrich creator/updater with display name + email for the Audit
	# Information section on the frontend. A shared cache avoids repeat
	# User lookups when several trainers share the same creator/updater.
	user_cache = {}
	for t in trainers:
		_attach_audit_info(t, user_cache)

	total = frappe.db.count("CRM Trainer", filters=_filters)

	return {
		"data": trainers,
		"total": total,
		"page": page,
		"page_length": page_length,
	}


@frappe.whitelist()
def create_trainer(trainer: str) -> dict:
	if isinstance(trainer, str):
		trainer = json.loads(trainer)
	_strip_audit_fields(trainer)

	doc = frappe.new_doc("CRM Trainer")
	doc.update(trainer)
	# `owner`/`creation` are set automatically by Frappe from
	# frappe.session.user and the current timestamp on insert.
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return _attach_audit_info(doc.as_dict())


@frappe.whitelist()
def update_trainer(name: str, trainer: str) -> dict:
	if isinstance(trainer, str):
		trainer = json.loads(trainer)
	_strip_audit_fields(trainer)

	doc = frappe.get_doc("CRM Trainer", name)
	doc.update(trainer)
	# `modified`/`modified_by` are set automatically by Frappe from
	# frappe.session.user and the current timestamp on save.
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return _attach_audit_info(doc.as_dict())


@frappe.whitelist()
def delete_trainer(name: str) -> dict:
	frappe.delete_doc("CRM Trainer", name, ignore_permissions=True)
	frappe.db.commit()
	return {"success": True}
