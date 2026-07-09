import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Coalesce, IfNull, Sum

MONTH_TO_NUM = {
	"January": 1, "February": 2, "March": 3, "April": 4,
	"May": 5, "June": 6, "July": 7, "August": 8,
	"September": 9, "October": 10, "November": 11, "December": 12,
}

QUARTER_MONTHS = {
	"Q1": (1, 3), "Q2": (4, 6), "Q3": (7, 9), "Q4": (10, 12),
}


def _get_period_dates(target_type: str, year: int, month: str | None, quarter: str | None):
	"""Resolve a target's period into concrete from_date/to_date strings."""
	if target_type == "Monthly":
		month_num = MONTH_TO_NUM[month]
		from_date = frappe.utils.get_first_day(f"{year}-{month_num:02d}-01")
		to_date = frappe.utils.get_last_day(from_date)
	elif target_type == "Quarterly":
		start_month, end_month = QUARTER_MONTHS[quarter]
		from_date = frappe.utils.get_first_day(f"{year}-{start_month:02d}-01")
		to_date = frappe.utils.get_last_day(f"{year}-{end_month:02d}-01")
	else:  # Yearly
		from_date = f"{year}-01-01"
		to_date = f"{year}-12-31"
	return str(from_date), str(to_date)


def _get_achieved_revenue(employee: str, from_date: str, to_date: str) -> float:
	"""
	Achieved Revenue = existing employee revenue calculation.

	Reuses the exact same filter pattern already used by
	crm.api.dashboard.get_won_deals (Won status + closed_date range)
	combined with the Sum(deal_value * exchange_rate) aggregation
	already used by crm.api.dashboard.get_deals_by_salesperson.
	No new revenue-calculation logic is introduced here.
	"""
	Deal = DocType("CRM Deal")
	Status = DocType("CRM Deal Status")

	to_date_plus_one = frappe.utils.add_days(to_date, 1)

	result = (
		frappe.qb.from_(Deal)
		.join(Status)
		.on(Deal.status == Status.name)
		.select(Sum(Coalesce(Deal.deal_value, 0) * IfNull(Deal.exchange_rate, 1)).as_("total"))
		.where(
			(Deal.deal_owner == employee)
			& (Deal.closed_date >= from_date)
			& (Deal.closed_date < to_date_plus_one)
			& (Status.type == "Won")
		)
		.run(as_dict=True)
	)
	return float(result[0].total or 0) if result else 0.0


def _get_status(achievement_percentage: float) -> str:
	if achievement_percentage >= 100:
		return "Completed"
	if achievement_percentage >= 70:
		return "On Track"
	return "Behind Target"


def _build_target_payload(target: dict) -> dict:
	from_date, to_date = _get_period_dates(
		target["target_type"], target["year"], target.get("month"), target.get("quarter")
	)
	achieved = _get_achieved_revenue(target["employee"], from_date, to_date)
	target_amount = float(target["target_amount"] or 0)
	remaining = target_amount - achieved
	achievement_percentage = (achieved / target_amount * 100) if target_amount else 0

	return {
		"name": target["name"],
		"employee": target["employee"],
		"target_type": target["target_type"],
		"year": target["year"],
		"month": target.get("month"),
		"quarter": target.get("quarter"),
		"target_amount": target_amount,
		"achieved_revenue": achieved,
		"remaining_revenue": remaining,
		"achievement_percentage": round(achievement_percentage, 1),
		"status": _get_status(achievement_percentage),
		"from_date": from_date,
		"to_date": to_date,
	}


def _is_admin() -> bool:
	return "System Manager" in frappe.get_roles()


@frappe.whitelist()
def get_current_target(employee: str | None = None) -> dict | None:
	"""
	Returns the most relevant target for the given employee:
	1. A target whose period actually covers today, if one exists.
	2. Otherwise, the most recently created target for that employee
	   (so admins see the target they just set even if it's for a
	   past or future period, instead of the card going blank).

	Non-admins can only ever fetch their own target, regardless of
	what `employee` is passed as.
	"""
	if not _is_admin():
		employee = frappe.session.user
	elif not employee:
		employee = frappe.session.user

	today = frappe.utils.nowdate()

	all_targets = frappe.get_all(
		"CRM Revenue Target",
		filters={"employee": employee},
		fields=["name", "target_type", "year", "month", "quarter", "target_amount", "creation"],
		order_by="creation desc",
	)

	if not all_targets:
		return None

	today_year = frappe.utils.getdate(today).year
	current_month_name = frappe.utils.formatdate(today, "MMMM")
	current_quarter = f"Q{(frappe.utils.getdate(today).month - 1) // 3 + 1}"

	this_year_targets = [t for t in all_targets if t.year == today_year]

	monthly = next(
		(t for t in this_year_targets if t.target_type == "Monthly" and t.month == current_month_name),
		None,
	)
	quarterly = next(
		(t for t in this_year_targets if t.target_type == "Quarterly" and t.quarter == current_quarter),
		None,
	)
	yearly = next((t for t in this_year_targets if t.target_type == "Yearly"), None)

	# Prefer a target that actually covers today (Monthly > Quarterly > Yearly).
	# Fall back to the most recently created target so the card never goes
	# blank just because the set period doesn't include today.
	match = monthly or quarterly or yearly or all_targets[0]

	return _build_target_payload(match)

@frappe.whitelist()
def list_targets(employee: str | None = None) -> list[dict]:
	"""Admin-only: list all targets, optionally filtered by employee."""
	frappe.only_for("System Manager", True)

	filters = {}
	if employee:
		filters["employee"] = employee

	targets = frappe.get_all(
		"CRM Revenue Target",
		filters=filters,
		fields=["name", "employee", "target_type", "year", "month", "quarter", "target_amount"],
		order_by="year desc, creation desc",
	)
	return [_build_target_payload(t) for t in targets]


@frappe.whitelist()
def create_target(target: str) -> dict:
	"""Admin-only: create a new Revenue Target."""
	frappe.only_for("System Manager", True)

	import json
	if isinstance(target, str):
		target = json.loads(target)

	doc = frappe.new_doc("CRM Revenue Target")
	doc.update(
		{
			"employee": target.get("employee"),
			"target_type": target.get("target_type"),
			"year": target.get("year"),
			"month": target.get("month"),
			"quarter": target.get("quarter"),
			"target_amount": target.get("target_amount"),
		}
	)
	doc.insert()
	frappe.db.commit()
	return _build_target_payload(doc.as_dict())


@frappe.whitelist()
def update_target(name: str, target: str) -> dict:
	"""Admin-only: update an existing Revenue Target."""
	frappe.only_for("System Manager", True)

	import json
	if isinstance(target, str):
		target = json.loads(target)

	doc = frappe.get_doc("CRM Revenue Target", name)
	for field in ["employee", "target_type", "year", "month", "quarter", "target_amount"]:
		if field in target:
			doc.set(field, target[field])
	doc.save()
	frappe.db.commit()
	return _build_target_payload(doc.as_dict())


@frappe.whitelist()
def delete_target(name: str) -> dict:
	"""Admin-only: delete a Revenue Target."""
	frappe.only_for("System Manager", True)
	frappe.delete_doc("CRM Revenue Target", name, ignore_permissions=True)
	frappe.db.commit()
	return {"success": True}
