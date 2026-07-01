import json

import frappe
from crm.api.session import get_session_role_flags


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

	# Enrich modified_by with full name for display
	for t in trainers:
		if t.get("modified_by"):
			t["modified_by_name"] = frappe.db.get_value(
				"User", t["modified_by"], "full_name"
			) or t["modified_by"]
		if t.get("owner"):
			t["owner_name"] = frappe.db.get_value(
				"User", t["owner"], "full_name"
			) or t["owner"]

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

	doc = frappe.new_doc("CRM Trainer")
	doc.update(trainer)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def update_trainer(name: str, trainer: str) -> dict:
	if isinstance(trainer, str):
		trainer = json.loads(trainer)

	doc = frappe.get_doc("CRM Trainer", name)
	doc.update(trainer)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def delete_trainer(name: str) -> dict:
	frappe.delete_doc("CRM Trainer", name, ignore_permissions=True)
	frappe.db.commit()
	return {"success": True}
