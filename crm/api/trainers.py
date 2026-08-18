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
def get_trainer_details(trainer: str) -> dict:
	"""
	Full details for a single trainer, for the Trainer ID hover-preview
	popup on the Deal's Data tab (Trainer Details section). Returns
	everything relevant to show in that popup in one call - identity,
	contact, skill/experience, availability/status, and commercial info.
	"""
	if not trainer or not frappe.db.exists("CRM Trainer", trainer):
		frappe.throw(frappe._("Trainer {0} not found").format(trainer))

	if not frappe.has_permission("CRM Trainer", "read", trainer):
		frappe.throw(frappe._("Not permitted to view this Trainer"), frappe.PermissionError)

	doc = frappe.get_cached_doc("CRM Trainer", trainer)

	data = {
		"name": doc.name,
		"trainer_name": doc.trainer_name,
		"phone": doc.phone,
		"alternate_phone": doc.alternate_phone,
		"email": doc.email,
		"linkedin_profile": doc.linkedin_profile,
		"location": doc.location,
		"technology_expert_in": doc.technology_expert_in,
		"skill_level": doc.skill_level,
		"experience": doc.experience,
		"availability": doc.availability,
		"status": doc.status,
		"commercial": doc.commercial,
		"commercial_type": doc.commercial_type,
		"company": doc.company,
	}

	return _attach_audit_info({**data, "owner": doc.owner, "modified_by": doc.modified_by})


@frappe.whitelist()
def get_trainer_locations() -> list:
	"""Distinct, non-empty `location` values already used by trainers.

	Powers the autocomplete suggestions on the Trainers list Location
	filter. Deliberately not a hard-restricted dropdown - location has no
	fixed option list on the doctype, so this only nudges toward existing
	values (e.g. avoiding "Bangalore" vs "bangalore" duplicates) without
	blocking a genuinely new location from being typed and searched.
	"""
	rows = frappe.get_all(
		"CRM Trainer",
		filters={"location": ["not in", ["", None]]},
		fields=["location"],
		distinct=True,
		order_by="location asc",
		ignore_permissions=True,
	)
	return [r["location"] for r in rows if r.get("location")]


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
	_or_filters = {}
	if search:
		like = ["like", f"%{search}%"]
		# Universal search: matches any of these fields, so a query like
		# "5 years" or "aws" or a phone/email fragment all work from the
		# single search box.
		_or_filters = {
			"trainer_name": like,
			"phone": like,
			"alternate_phone": like,
			"email": like,
			"technology_expert_in": like,
			"experience": like,
		}

	if filters:
		if isinstance(filters, str):
			filters = json.loads(filters)
		_filters.update(filters)

	offset = (page - 1) * page_length

	list_kwargs = dict(filters=_filters, ignore_permissions=True)
	if _or_filters:
		list_kwargs["or_filters"] = _or_filters

	trainers = frappe.get_all(
		"CRM Trainer",
		fields=[
			"name",
			"trainer_name",
			"phone",
			"alternate_phone",
			"email",
			"linkedin_profile",
			"location",
			"technology_expert_in",
			"skill_level",
			"experience",
			"availability",
			"status",
			"commercial",
			"commercial_type",
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
		**list_kwargs,
	)

	# Enrich creator/updater with display name + email for the Audit
	# Information section on the frontend. A shared cache avoids repeat
	# User lookups when several trainers share the same creator/updater.
	user_cache = {}
	for t in trainers:
		_attach_audit_info(t, user_cache)

	# NOTE: intentionally not using an aggregate `count(name)` query here -
	# combined with Frappe's default `order by modified desc`, that can
	# fail under MySQL's ONLY_FULL_GROUP_BY strict mode (ORDER BY on a
	# non-aggregated/non-grouped column). Fetching just `name` with no
	# ordering avoids that entirely and is plenty fast at this table size.
	total = len(
		frappe.get_all(
			"CRM Trainer",
			fields=["name"],
			order_by=None,
			limit_page_length=0,
			**list_kwargs,
		)
	)

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
