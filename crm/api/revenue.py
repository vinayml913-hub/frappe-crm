"""
Revenue Analytics API
======================

Revenue source of truth
------------------------
Revenue is calculated exclusively from **CRM Deal** records whose linked
**CRM Deal Status** has ``type == "Won"`` (the same definition the existing
CRM Dashboard uses — see ``crm/api/dashboard.py``).

Revenue amount per deal = ``deal_value * COALESCE(exchange_rate, 1)``
(same formula already used in ``get_average_won_deal_value``).

The deal's owner (``deal_owner``) is treated as the "employee" who
generated that revenue.

Access model
------------
- System Manager / Sales Manager -> "Admin" view: can see all employees,
  filter by any user, see company-wide totals.
- Everyone else ("Employee" view): every endpoint is silently scoped to
  ``frappe.session.user`` regardless of any userId filter passed in,
  so an employee can never see another employee's revenue.

No Department/Team filtering is implemented (none exists in this schema) -
only date range and individual user (userId) filters are supported, as
requested.
"""

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum, IfNull, Count
from frappe.utils import (
    getdate,
    get_first_day,
    get_last_day,
    add_months,
    nowdate,
    flt,
)


# ─────────────────────────────────────────────────────────────────────────
#  Access helpers
# ─────────────────────────────────────────────────────────────────────────

def _is_admin():
    roles = frappe.get_roles(frappe.session.user)
    return "System Manager" in roles or "Sales Manager" in roles


def _resolve_scope(user_id):
    """
    Returns the effective user filter to apply.
    - Admins: whatever userId was requested (None = all employees).
    - Non-admins: always forced to their own session user.
    """
    if _is_admin():
        return user_id or None
    return frappe.session.user


# ─────────────────────────────────────────────────────────────────────────
#  Date helpers
# ─────────────────────────────────────────────────────────────────────────

def _default_date_range(from_date, to_date):
    """Default to the current month if no range given."""
    if not from_date or not to_date:
        today = nowdate()
        from_date = from_date or get_first_day(today)
        to_date = to_date or get_last_day(today)
    return getdate(from_date), getdate(to_date)


def _period_bounds(period_type, year, month=None, quarter=None):
    """Return (from_date, to_date) for a Monthly / Quarterly / Yearly period."""
    year = int(year)
    if period_type == "Monthly":
        month = int(month)
        start = getdate(f"{year}-{month:02d}-01")
        end = get_last_day(start)
    elif period_type == "Quarterly":
        q_start_month = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}[quarter]
        start = getdate(f"{year}-{q_start_month:02d}-01")
        end = get_last_day(add_months(start, 2))
    else:  # Yearly
        start = getdate(f"{year}-01-01")
        end = getdate(f"{year}-12-31")
    return start, end


# ─────────────────────────────────────────────────────────────────────────
#  Core query builder — shared by every endpoint
# ─────────────────────────────────────────────────────────────────────────

def _won_deal_query(from_date, to_date, user=None):
    """
    Base query builder for Won deals in a date range, optionally for one user.
    Filters on closed_date (falls back to modified for legacy data without
    closed_date set, mirroring how the existing dashboard treats this field).
    Returns a pypika query builder ready for .select(...)
    """
    Deal = DocType("CRM Deal")
    Status = DocType("CRM Deal Status")

    to_date_plus_one = frappe.utils.add_days(to_date, 1)

    query = (
        frappe.qb.from_(Deal)
        .join(Status)
        .on(Deal.status == Status.name)
        .where(Status.type == "Won")
        .where(Deal.closed_date.isnotnull())
        .where(Deal.closed_date >= from_date)
        .where(Deal.closed_date < to_date_plus_one)
    )

    if user:
        query = query.where(Deal.deal_owner == user)

    return query, Deal, Status


def _revenue_expr(Deal):
    """Revenue per deal = deal_value * exchange_rate (defaults to 1)."""
    return Deal.deal_value * IfNull(Deal.exchange_rate, 1)


# ─────────────────────────────────────────────────────────────────────────
#  1. GET /reports/revenue-summary
#     -> crm.api.revenue.get_revenue_summary
# ─────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_revenue_summary(fromDate=None, toDate=None, userId=None):
    """
    KPI card data.

    Admin payload includes company-wide totals + per-employee averages.
    Employee payload is scoped to the caller only.
    """
    from_date, to_date = _default_date_range(fromDate, toDate)
    scoped_user = _resolve_scope(userId)
    is_admin = _is_admin()

    def _sum_revenue(f_date, t_date, user=None):
        query, Deal, Status = _won_deal_query(f_date, t_date, user)
        result = query.select(
            Sum(_revenue_expr(Deal)).as_("revenue"),
            Count(Deal.name).as_("deal_count"),
        ).run(as_dict=True)
        row = result[0] if result else {}
        return flt(row.get("revenue") or 0), int(row.get("deal_count") or 0)

    # Month-to-date / quarter-to-date / year-to-date bounds, always anchored
    # on "today" regardless of the from/to filter, since these are fixed
    # rolling KPIs ("My Monthly Revenue" etc.) rather than range-filtered.
    today = getdate(nowdate())
    month_start, month_end = get_first_day(today), get_last_day(today)

    q_month = (today.month - 1) // 3 * 3 + 1
    quarter_start = getdate(f"{today.year}-{q_month:02d}-01")
    quarter_end = get_last_day(add_months(quarter_start, 2))

    year_start = getdate(f"{today.year}-01-01")
    year_end = getdate(f"{today.year}-12-31")

    if not is_admin:
        # ── EMPLOYEE VIEW ───────────────────────────────────────────
        user = scoped_user
        range_revenue, range_deals = _sum_revenue(from_date, to_date, user)
        month_revenue, _m = _sum_revenue(month_start, month_end, user)
        quarter_revenue, _q = _sum_revenue(quarter_start, quarter_end, user)
        year_revenue, _y = _sum_revenue(year_start, year_end, user)

        return {
            "scope": "employee",
            "user": user,
            "from_date": str(from_date),
            "to_date": str(to_date),
            "cards": {
                "my_revenue_generated": range_revenue,
                "my_won_deal_revenue": range_revenue,
                "my_won_deal_count": range_deals,
                "my_monthly_revenue": month_revenue,
                "my_quarterly_revenue": quarter_revenue,
                "my_yearly_revenue": year_revenue,
            },
        }

    # ── ADMIN VIEW ───────────────────────────────────────────────────
    # If a specific userId was requested even as admin, narrow totals to
    # that one user; otherwise compute company-wide.
    total_revenue, total_deals = _sum_revenue(from_date, to_date, scoped_user)
    month_revenue, _m = _sum_revenue(month_start, month_end, scoped_user)
    quarter_revenue, _q = _sum_revenue(quarter_start, quarter_end, scoped_user)
    year_revenue, _y = _sum_revenue(year_start, year_end, scoped_user)

    # Average revenue per employee + top performer — always company-wide,
    # not narrowed by userId (these are inherently cross-employee metrics).
    Deal = DocType("CRM Deal")
    Status = DocType("CRM Deal Status")
    by_employee_query, _, _ = _won_deal_query(from_date, to_date, None)
    by_employee = (
        by_employee_query.select(
            Deal.deal_owner.as_("user"),
            Sum(_revenue_expr(Deal)).as_("revenue"),
        )
        .groupby(Deal.deal_owner)
        .run(as_dict=True)
    )

    employee_count = len(by_employee)
    avg_revenue_per_employee = (total_revenue / employee_count) if employee_count else 0

    top_employee = None
    if by_employee:
        top_row = max(by_employee, key=lambda r: flt(r.get("revenue") or 0))
        top_employee = {
            "user": top_row["user"],
            "full_name": frappe.db.get_value("User", top_row["user"], "full_name") or top_row["user"],
            "revenue": flt(top_row.get("revenue") or 0),
        }

    return {
        "scope": "admin",
        "user": scoped_user,
        "from_date": str(from_date),
        "to_date": str(to_date),
        "cards": {
            "total_company_revenue": total_revenue,
            "total_revenue_generated_by_all_employees": total_revenue,
            "total_won_deals": total_deals,
            "monthly_revenue": month_revenue,
            "quarterly_revenue": quarter_revenue,
            "yearly_revenue": year_revenue,
            "average_revenue_per_employee": avg_revenue_per_employee,
            "top_revenue_generating_employee": top_employee,
            "active_employee_count": employee_count,
        },
    }


# ─────────────────────────────────────────────────────────────────────────
#  2. GET /reports/revenue-by-employee
#     -> crm.api.revenue.get_revenue_by_employee
# ─────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_revenue_by_employee(fromDate=None, toDate=None, userId=None):
    """
    Bar chart data: revenue per employee.

    Employees get a single-row list containing only themselves
    (so the same chart component can render either view safely).
    """
    from_date, to_date = _default_date_range(fromDate, toDate)
    scoped_user = _resolve_scope(userId)

    query, Deal, Status = _won_deal_query(from_date, to_date, scoped_user)
    rows = (
        query.select(
            Deal.deal_owner.as_("user"),
            Sum(_revenue_expr(Deal)).as_("revenue"),
            Count(Deal.name).as_("won_deals"),
        )
        .groupby(Deal.deal_owner)
        .orderby(Sum(_revenue_expr(Deal)), order=frappe.qb.desc)
        .run(as_dict=True)
    )

    # Attach display names
    user_names = _bulk_user_names([r["user"] for r in rows])
    for r in rows:
        r["revenue"] = flt(r.get("revenue") or 0)
        r["employee_name"] = user_names.get(r["user"], r["user"])

    return {
        "from_date": str(from_date),
        "to_date": str(to_date),
        "data": rows,
        # Ready-to-render config for frappe-ui's <AxisChart>
        "chart": {
            "data": rows,
            "title": _("Revenue by Employee"),
            "xAxis": {"title": _("Employee"), "key": "employee_name", "type": "category"},
            "yAxis": {"title": _("Revenue")},
            "series": [{"name": "revenue", "type": "bar"}],
        },
    }


# ─────────────────────────────────────────────────────────────────────────
#  3. GET /reports/revenue-trends
#     -> crm.api.revenue.get_revenue_trends
# ─────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_revenue_trends(fromDate=None, toDate=None, userId=None, granularity="month"):
    """
    Line chart data: revenue trend over time (month buckets by default).

    Always returns buckets in chronological order, including months in the
    range that had zero revenue (so the line doesn't visually skip gaps).
    """
    from_date, to_date = _default_date_range(fromDate, toDate)
    scoped_user = _resolve_scope(userId)

    query, Deal, Status = _won_deal_query(from_date, to_date, scoped_user)

    # MySQL/MariaDB month-bucket key as YYYY-MM
    from frappe.query_builder.functions import DateFormat

    rows = (
        query.select(
            DateFormat(Deal.closed_date, "%Y-%m").as_("period"),
            Sum(_revenue_expr(Deal)).as_("revenue"),
            Count(Deal.name).as_("won_deals"),
        )
        .groupby(DateFormat(Deal.closed_date, "%Y-%m"))
        .orderby(DateFormat(Deal.closed_date, "%Y-%m"))
        .run(as_dict=True)
    )

    revenue_by_period = {r["period"]: flt(r.get("revenue") or 0) for r in rows}
    deals_by_period = {r["period"]: int(r.get("won_deals") or 0) for r in rows}

    # Build a complete chronological list of months between from_date/to_date
    buckets = []
    cursor = get_first_day(from_date)
    end_marker = get_first_day(to_date)
    while cursor <= end_marker:
        key = cursor.strftime("%Y-%m")
        buckets.append({
            "period": key,
            "label": cursor.strftime("%b %Y"),
            "revenue": revenue_by_period.get(key, 0),
            "won_deals": deals_by_period.get(key, 0),
        })
        cursor = add_months(cursor, 1)

    # Growth = % change vs previous bucket
    for i, b in enumerate(buckets):
        if i == 0:
            b["growth_pct"] = 0
        else:
            prev = buckets[i - 1]["revenue"]
            b["growth_pct"] = ((b["revenue"] - prev) / prev * 100) if prev else (100 if b["revenue"] else 0)

    total_revenue = sum(b["revenue"] for b in buckets)

    return {
        "from_date": str(from_date),
        "to_date": str(to_date),
        "total_revenue": total_revenue,
        "data": buckets,
        "chart": {
            "data": buckets,
            "title": _("Monthly Revenue Trend"),
            "xAxis": {"title": _("Month"), "key": "label", "type": "category"},
            "yAxis": {"title": _("Revenue")},
            "series": [{"name": "revenue", "type": "line", "showDataPoints": True}],
        },
    }


# ─────────────────────────────────────────────────────────────────────────
#  4. GET /reports/top-performers
#     -> crm.api.revenue.get_top_performers
# ─────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_top_performers(fromDate=None, toDate=None, userId=None, limit=10):
    """
    Leaderboard table: Rank, Employee, Revenue, Won Deals, Achievement %,
    Contribution %.

    Achievement % needs a CRM Revenue Target for the matching period; if
    none exists for a user, achievement_pct is returned as None (frontend
    should render "—").
    """
    from_date, to_date = _default_date_range(fromDate, toDate)
    scoped_user = _resolve_scope(userId)
    limit = int(limit) if limit else 10

    query, Deal, Status = _won_deal_query(from_date, to_date, scoped_user)

    rows = (
        query.select(
            Deal.deal_owner.as_("user"),
            Sum(_revenue_expr(Deal)).as_("revenue"),
            Count(Deal.name).as_("won_deals"),
        )
        .groupby(Deal.deal_owner)
        .orderby(Sum(_revenue_expr(Deal)), order=frappe.qb.desc)
        .limit(limit)
        .run(as_dict=True)
    )

    total_company_revenue = _company_total_revenue(from_date, to_date)
    user_names = _bulk_user_names([r["user"] for r in rows])

    results = []
    for idx, r in enumerate(rows, start=1):
        revenue = flt(r.get("revenue") or 0)
        won_deals = int(r.get("won_deals") or 0)
        contribution_pct = (revenue / total_company_revenue * 100) if total_company_revenue else 0
        target = _get_target_for_range(r["user"], from_date, to_date)
        achievement_pct = (revenue / target * 100) if target else None

        results.append({
            "rank": idx,
            "user": r["user"],
            "employee_name": user_names.get(r["user"], r["user"]),
            "revenue_generated": revenue,
            "won_deals": won_deals,
            "target_amount": target,
            "achievement_pct": achievement_pct,
            "revenue_contribution_pct": contribution_pct,
        })

    return {
        "from_date": str(from_date),
        "to_date": str(to_date),
        "total_company_revenue": total_company_revenue,
        "data": results,
    }


# ─────────────────────────────────────────────────────────────────────────
#  5. GET /reports/revenue-target-comparison
#     -> crm.api.revenue.get_revenue_target_comparison
# ─────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_revenue_target_comparison(fromDate=None, toDate=None, userId=None):
    """
    Bar chart data: Target vs Actual, per employee + an "Overall Company" row.

    Targets are matched from CRM Revenue Target by finding any target
    records whose period overlaps the requested date range, summed per user.
    """
    from_date, to_date = _default_date_range(fromDate, toDate)
    scoped_user = _resolve_scope(userId)

    query, Deal, Status = _won_deal_query(from_date, to_date, scoped_user)
    actual_rows = (
        query.select(
            Deal.deal_owner.as_("user"),
            Sum(_revenue_expr(Deal)).as_("revenue"),
        )
        .groupby(Deal.deal_owner)
        .run(as_dict=True)
    )

    user_names = _bulk_user_names([r["user"] for r in actual_rows])

    results = []
    total_target = 0
    total_actual = 0

    for r in actual_rows:
        actual = flt(r.get("revenue") or 0)
        target = _get_target_for_range(r["user"], from_date, to_date) or 0
        total_target += target
        total_actual += actual
        results.append({
            "user": r["user"],
            "employee_name": user_names.get(r["user"], r["user"]),
            "target_amount": target,
            "actual_revenue": actual,
            "achievement_pct": (actual / target * 100) if target else None,
        })

    existing_users = {r["user"] for r in results}
    target_filters = {
        "year": ["in", _years_in_range(from_date, to_date)],
    }
    if scoped_user:
        target_filters["user"] = scoped_user

    target_only_users = frappe.get_all(
        "CRM Revenue Target",
        filters=target_filters,
        fields=["user"],
        distinct=True,
        ignore_permissions=True,
    )
    for t in target_only_users:
        if t["user"] not in existing_users:
            target = _get_target_for_range(t["user"], from_date, to_date) or 0
            if target:
                total_target += target
                results.append({
                    "user": t["user"],
                    "employee_name": _bulk_user_names([t["user"]]).get(t["user"], t["user"]),
                    "target_amount": target,
                    "actual_revenue": 0,
                    "achievement_pct": 0,
                })
                existing_users.add(t["user"])

    results.sort(key=lambda r: r["actual_revenue"], reverse=True)

    overall = {
        "user": None,
        "employee_name": _("Overall Company"),
        "target_amount": total_target,
        "actual_revenue": total_actual,
        "achievement_pct": (total_actual / total_target * 100) if total_target else None,
    }

    chart_rows = [
        {"employee_name": r["employee_name"], "target": r["target_amount"], "actual": r["actual_revenue"]}
        for r in results
    ]

    return {
        "from_date": str(from_date),
        "to_date": str(to_date),
        "overall": overall,
        "data": results,
        "chart": {
            "data": chart_rows,
            "title": _("Revenue vs Target"),
            "xAxis": {"title": _("Employee"), "key": "employee_name", "type": "category"},
            "yAxis": {"title": _("Amount")},
            "series": [
                {"name": "target", "type": "bar"},
                {"name": "actual", "type": "bar"},
            ],
        },
    }


# ─────────────────────────────────────────────────────────────────────────
#  6. Revenue Contribution (Donut) — supporting endpoint
#     -> crm.api.revenue.get_revenue_contribution
# ─────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_revenue_contribution(fromDate=None, toDate=None, userId=None):
    """
    Donut chart data: % contribution of each employee to total revenue
    in the selected range.
    """
    from_date, to_date = _default_date_range(fromDate, toDate)
    scoped_user = _resolve_scope(userId)

    query, Deal, Status = _won_deal_query(from_date, to_date, scoped_user)
    rows = (
        query.select(
            Deal.deal_owner.as_("user"),
            Sum(_revenue_expr(Deal)).as_("revenue"),
        )
        .groupby(Deal.deal_owner)
        .orderby(Sum(_revenue_expr(Deal)), order=frappe.qb.desc)
        .run(as_dict=True)
    )

    total = sum(flt(r.get("revenue") or 0) for r in rows)
    user_names = _bulk_user_names([r["user"] for r in rows])

    data = []
    for r in rows:
        revenue = flt(r.get("revenue") or 0)
        data.append({
            "user": r["user"],
            "employee_name": user_names.get(r["user"], r["user"]),
            "revenue": revenue,
            "contribution_pct": (revenue / total * 100) if total else 0,
        })

    return {
        "from_date": str(from_date),
        "to_date": str(to_date),
        "total_revenue": total,
        "data": data,
        "chart": {
            "data": [{"employee_name": d["employee_name"], "count": d["revenue"]} for d in data],
            "title": _("Revenue Contribution"),
            "categoryColumn": "employee_name",
            "valueColumn": "count",
        },
    }


# ─────────────────────────────────────────────────────────────────────────
#  Target CRUD (Admin only) — used by the "manage targets" UI
# ─────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_revenue_targets(userId=None, year=None):
    """List existing targets, optionally filtered by user/year. Admin only."""
    if not _is_admin():
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    filters = {}
    if userId:
        filters["user"] = userId
    if year:
        filters["year"] = year

    return frappe.get_all(
        "CRM Revenue Target",
        filters=filters,
        fields=["name", "user", "period_type", "year", "month", "quarter", "period_label", "target_amount", "currency"],
        order_by="year desc, period_label desc",
        ignore_permissions=True,
    )


@frappe.whitelist()
def set_revenue_target(data):
    """
    Create or update a revenue target. Admin only.
    `data` is a JSON string/dict with: user, period_type, year, month/quarter,
    target_amount, and optionally `name` to update an existing record.
    """
    import json

    if not _is_admin():
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    if isinstance(data, str):
        data = json.loads(data)

    name = data.get("name")
    if name and frappe.db.exists("CRM Revenue Target", name):
        doc = frappe.get_doc("CRM Revenue Target", name)
    else:
        doc = frappe.new_doc("CRM Revenue Target")

    for field in ("user", "period_type", "year", "month", "quarter", "target_amount", "currency", "notes"):
        if field in data:
            setattr(doc, field, data[field])

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return doc.as_dict()


@frappe.whitelist()
def delete_revenue_target(name):
    if not _is_admin():
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    frappe.delete_doc("CRM Revenue Target", name, ignore_permissions=True)
    frappe.db.commit()
    return {"deleted": name}


# ─────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────

def _bulk_user_names(user_ids):
    """Batch-fetch full_name for a list of user emails. Returns {email: full_name}."""
    user_ids = [u for u in set(user_ids) if u]
    if not user_ids:
        return {}
    rows = frappe.get_all(
        "User",
        filters={"name": ["in", user_ids]},
        fields=["name", "full_name"],
        ignore_permissions=True,
    )
    return {r["name"]: (r["full_name"] or r["name"]) for r in rows}


def _company_total_revenue(from_date, to_date):
    query, Deal, Status = _won_deal_query(from_date, to_date, None)
    result = query.select(Sum(_revenue_expr(Deal)).as_("revenue")).run(as_dict=True)
    return flt(result[0].get("revenue") or 0) if result else 0


def _years_in_range(from_date, to_date):
    return list(range(getdate(from_date).year, getdate(to_date).year + 1))


def _get_target_for_range(user, from_date, to_date):
    """
    Sum all CRM Revenue Target rows for `user` whose period overlaps
    [from_date, to_date]. Handles Monthly/Quarterly/Yearly targets uniformly
    by resolving each target row to its own date range and checking overlap.
    """
    if not user:
        return 0

    targets = frappe.get_all(
        "CRM Revenue Target",
        filters={"user": user, "year": ["in", _years_in_range(from_date, to_date)]},
        fields=["period_type", "year", "month", "quarter", "target_amount"],
        ignore_permissions=True,
    )

    from_date = getdate(from_date)
    to_date = getdate(to_date)
    total = 0

    for t in targets:
        t_start, t_end = _period_bounds(t["period_type"], t["year"], t.get("month"), t.get("quarter"))
        # Overlap check
        if t_start <= to_date and t_end >= from_date:
            total += flt(t.get("target_amount") or 0)

    return total
