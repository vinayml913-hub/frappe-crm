import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import flt
from pypika import Case

MONTH_TO_NUM = {
	"January": 1, "February": 2, "March": 3, "April": 4,
	"May": 5, "June": 6, "July": 7, "August": 8,
	"September": 9, "October": 10, "November": 11, "December": 12,
}

# ─────────────────────────────────────────────────────────────────────────
#  Company financial quarters (NOT calendar quarters)
#
#    Q1 = March     1 - May      31  (start month 3,  end month 5,  same year)
#    Q2 = June      1 - August   31  (start month 6,  end month 8,  same year)
#    Q3 = September 1 - November 30  (start month 9,  end month 11, same year)
#    Q4 = December  1 - February 28/29 (start month 12, same year;
#                                        end month 2, following year)
#
#  A quarter's "year" always refers to the fiscal year it belongs to, i.e.
#  the year of its *start* month. Q4 therefore spans a calendar year
#  boundary: Q4 2025 runs from 1 Dec 2025 through 28/29 Feb 2026.
# ─────────────────────────────────────────────────────────────────────────
QUARTER_MONTHS = {
	"Q1": (3, 5, 0),
	"Q2": (6, 8, 0),
	"Q3": (9, 11, 0),
	"Q4": (12, 2, 1),
}


def get_financial_quarter_for_date(date) -> tuple[str, int]:
	"""Given any date, return (quarter, fiscal_year) using the company's
	Mar-Feb financial quarters. Fiscal year is the year of the quarter's
	start month (so Jan/Feb dates belong to Q4 of the *previous* year)."""
	date = frappe.utils.getdate(date)
	month, year = date.month, date.year
	if month in (3, 4, 5):
		return "Q1", year
	if month in (6, 7, 8):
		return "Q2", year
	if month in (9, 10, 11):
		return "Q3", year
	# month in (12, 1, 2)
	if month == 12:
		return "Q4", year
	return "Q4", year - 1


def get_financial_quarter_bounds(quarter: str, year: int):
	"""Return (from_date, to_date) as date objects for a given quarter/fiscal year."""
	year = int(year)
	start_month, end_month, end_year_offset = QUARTER_MONTHS[quarter]
	from_date = frappe.utils.get_first_day(f"{year}-{start_month:02d}-01")
	to_date = frappe.utils.get_last_day(f"{year + end_year_offset}-{end_month:02d}-01")
	return from_date, to_date


def _get_period_dates(target_type: str, year: int, month: str | None, quarter: str | None):
	"""Resolve a target's period into concrete from_date/to_date strings."""
	if target_type == "Monthly":
		month_num = MONTH_TO_NUM[month]
		from_date = frappe.utils.get_first_day(f"{year}-{month_num:02d}-01")
		to_date = frappe.utils.get_last_day(from_date)
	elif target_type == "Quarterly":
		from_date, to_date = get_financial_quarter_bounds(quarter, year)
	else:  # Yearly
		from_date = f"{year}-01-01"
		to_date = f"{year}-12-31"
	return str(from_date), str(to_date)


def _get_achieved_revenue(employee: str, from_date: str, to_date: str) -> float:
	"""
	Achieved Revenue = existing employee revenue calculation.

	PBS Deal's actual client-facing amount is NOT the stock `deal_value`
	field - it's `training_commercial` when the sales rep fills it in
	directly, or the auto-calculated `final_amount` (from
	CRMDeal.calculate_financials: Trainer Cost + Margin% + GST) when
	left blank.
	"""
	Deal = DocType("CRM Deal")
	Status = DocType("CRM Deal Status")

	to_date_plus_one = frappe.utils.add_days(to_date, 1)

	revenue_amount = Case().when(
		Coalesce(Deal.training_commercial, 0) > 0,
		Deal.training_commercial,
	).else_(Coalesce(Deal.final_amount, 0))

	result = (
		frappe.qb.from_(Deal)
		.join(Status)
		.on(Deal.status == Status.name)
		.select(Sum(revenue_amount).as_("total"))
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
def get_target_for_period(employee: str | None = None, period: str | None = None) -> dict | None:
	"""
	Returns the target relevant to the dashboard's *currently selected*
	date filter, instead of always the target that covers today.

	`period` (from the Dashboard filter dropdown) is one of:
	  - None / "last_30_days"  -> same as get_current_target: whichever
	    target (Monthly > Quarterly > Yearly) actually covers today.
	  - "q1" / "q2" / "q3" / "q4" -> ONLY that quarter's Quarterly target,
	    for the fiscal year the current date belongs to. Nothing from
	    other quarters, months, or yearly targets is mixed in.
	  - "ever" -> a combined, all-time view: every target ever set for
	    the employee is summed for "Target", and achieved revenue is
	    computed with no date bound.

	Non-admins can only ever fetch their own target, regardless of what
	`employee` is passed as.
	"""
	if not _is_admin():
		employee = frappe.session.user
	elif not employee:
		employee = frappe.session.user

	period = (period or "last_30_days").lower()
	today = frappe.utils.nowdate()

	QUARTER_KEYS = {"q1": "Q1", "q2": "Q2", "q3": "Q3", "q4": "Q4"}

	if period in QUARTER_KEYS:
		quarter = QUARTER_KEYS[period]
		_current_quarter, current_quarter_year = get_financial_quarter_for_date(today)

		match = frappe.get_all(
			"CRM Revenue Target",
			filters={
				"employee": employee,
				"target_type": "Quarterly",
				"quarter": quarter,
				"year": current_quarter_year,
			},
			fields=["name", "employee", "target_type", "year", "month", "quarter", "target_amount", "creation"],
			limit_page_length=1,
		)
		if not match:
			return None
		return _build_target_payload(match[0])

	if period == "ever":
		all_targets = frappe.get_all(
			"CRM Revenue Target",
			filters={"employee": employee},
			fields=["target_amount"],
		)
		if not all_targets:
			return None

		target_amount = sum(flt(t.target_amount) for t in all_targets)
		achieved = _get_achieved_revenue(employee, "1900-01-01", frappe.utils.nowdate())
		remaining = target_amount - achieved
		achievement_percentage = (achieved / target_amount * 100) if target_amount else 0

		return {
			"name": None,
			"employee": employee,
			"target_type": "Overall",
			"year": None,
			"month": None,
			"quarter": None,
			"target_amount": target_amount,
			"achieved_revenue": achieved,
			"remaining_revenue": remaining,
			"achievement_percentage": round(achievement_percentage, 1),
			"status": _get_status(achievement_percentage),
			"from_date": None,
			"to_date": frappe.utils.nowdate(),
		}

	# "last_30_days" (default / fallback) -> same behaviour as before:
	# whichever target actually covers today.
	return get_current_target(employee=employee)


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
		fields=["name", "employee", "target_type", "year", "month", "quarter", "target_amount", "creation"],
		order_by="creation desc",
	)

	if not all_targets:
		return None

	today_year = frappe.utils.getdate(today).year
	current_month_name = frappe.utils.formatdate(today, "MMMM")
	current_quarter, current_quarter_year = get_financial_quarter_for_date(today)

	this_year_targets = [t for t in all_targets if t.year == today_year]
	this_fiscal_year_targets = [t for t in all_targets if t.year == current_quarter_year]

	monthly = next(
		(t for t in this_year_targets if t.target_type == "Monthly" and t.month == current_month_name),
		None,
	)
	quarterly = next(
		(t for t in this_fiscal_year_targets if t.target_type == "Quarterly" and t.quarter == current_quarter),
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
