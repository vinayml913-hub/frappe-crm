import frappe
import json
from frappe import _


# ─────────────────────────────────────────────
#  READ
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_sales_orders():
    """Return Sales Orders visible to the current user."""
    session_roles = frappe.get_roles()
    is_admin   = "System Manager" in session_roles
    is_manager = "Sales Manager"  in session_roles

    filters     = {"status": ["not in", ["Cancelled", "Archived"]]}
    or_filters  = None

    if not (is_admin or is_manager):
        current_user = frappe.session.user
        or_filters = [
            ["sales_manager",   "=", current_user],
            ["account_manager", "=", current_user],
        ]

    orders = frappe.get_all(
        "PBS Sales Order",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name", "deal", "organization", "contact_person", "company",
            "email", "phone", "status", "amount", "total_expense",
            "gross_profit", "gross_profit_percentage", "tax", "discount",
            "final_amount", "payment_status", "sales_manager", "account_manager",
            "delivery_manager", "technology", "trainer_assigned", "delivery_type",
            "project_duration", "start_date", "end_date", "delivery_date",
            "lab_required", "training_required", "notes", "modified",
        ],
        order_by="modified desc",
        ignore_permissions=True,
    )

    for order in orders:
        order["delivery_orders"] = frappe.get_all(
            "PBS Delivery Order",
            filters={"parent": order["name"], "parenttype": "PBS Sales Order"},
            fields=[
                "name", "product_code", "item", "description",
                "delivery_product_type", "qty", "rate", "amount", "status",
                "start_date", "end_date", "delivery_order_number", "account",
                "sales_manager", "account_manager", "delivery_person", "trainers",
            ],
            order_by="idx asc",
            ignore_permissions=True,
        )

    return orders


@frappe.whitelist()
def get_sales_order(name):
    """Return a single Sales Order as dict."""
    doc = frappe.get_doc("PBS Sales Order", name)
    return doc.as_dict()


# ─────────────────────────────────────────────
#  UPDATE SALES ORDER
# ─────────────────────────────────────────────

@frappe.whitelist()
def update_sales_order(name, data):
    """
    Update allowed fields on a PBS Sales Order.
    Accepts data as a JSON string or dict.
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, ValueError) as e:
            frappe.throw(_("Invalid JSON in data parameter: {0}").format(str(e)))

    if not isinstance(data, dict):
        frappe.throw(_("data must be a JSON object / dict"))

    doc = frappe.get_doc("PBS Sales Order", name)

    allowed = [
        "status", "amount", "total_expense", "tax", "discount",
        "technology", "trainer_assigned", "delivery_type", "project_duration",
        "start_date", "end_date", "delivery_date", "sales_manager",
        "account_manager", "delivery_manager", "payment_status",
        "email", "phone", "company", "contact_person", "notes",
        "lab_required", "training_required",
    ]

    for key in allowed:
        if key in data:
            value = data[key]
            # Normalise empty strings to None for non-text fields
            if value == "" and key not in ("notes", "email", "phone", "company",
                                           "technology", "project_duration"):
                value = None
            setattr(doc, key, value)

    try:
        doc.save(ignore_permissions=True)
        frappe.db.commit()
    except frappe.exceptions.ValidationError as e:
        frappe.log_error(
            title="update_sales_order ValidationError",
            message=frappe.get_traceback(),
        )
        frappe.throw(_("Validation failed: {0}").format(str(e)))
    except Exception as e:
        frappe.log_error(
            title="update_sales_order Error",
            message=frappe.get_traceback(),
        )
        frappe.throw(_("Could not save Sales Order: {0}").format(str(e)))

    return doc.as_dict()


# ─────────────────────────────────────────────
#  CREATE DELIVERY ORDER
# ─────────────────────────────────────────────

# Valid status values that match PBS Delivery Order DocType options
_VALID_DO_STATUSES = {"Open", "In Progress", "Delivered", "Cancelled", "On Hold"}

# Frontend → DocType status mapping (handles legacy / UI values)
_DO_STATUS_MAP = {
    "Pending":     "Open",
    "In Transit":  "In Progress",
    "pending":     "Open",
    "in transit":  "In Progress",
    "delivered":   "Delivered",
    "cancelled":   "Cancelled",
    "on hold":     "On Hold",
}


@frappe.whitelist()
def create_delivery_order(sales_order_name, delivery_order):
    """
    Append a new PBS Delivery Order row to a PBS Sales Order.
    Returns the updated list of delivery order rows.
    """
    if isinstance(delivery_order, str):
        try:
            delivery_order = json.loads(delivery_order)
        except (json.JSONDecodeError, ValueError) as e:
            frappe.throw(_("Invalid JSON in delivery_order parameter: {0}").format(str(e)))

    if not isinstance(delivery_order, dict):
        frappe.throw(_("delivery_order must be a JSON object / dict"))

    # ── Required field validation ──────────────────────────────────────
    item = (delivery_order.get("item") or "").strip()
    if not item:
        frappe.throw(_("Item / Delivery Title is required"))

    # ── Numeric coercion ───────────────────────────────────────────────
    try:
        qty = float(delivery_order.get("qty") or 1)
        if qty <= 0:
            qty = 1
    except (TypeError, ValueError):
        qty = 1

    try:
        rate = float(delivery_order.get("rate") or 0)
    except (TypeError, ValueError):
        rate = 0.0

    amount = qty * rate

    # ── Status normalisation ───────────────────────────────────────────
    raw_status = delivery_order.get("status") or "Open"
    status = _DO_STATUS_MAP.get(raw_status, raw_status)
    if status not in _VALID_DO_STATUSES:
        status = "Open"   # safe default instead of throwing

    # ── Build clean row dict ───────────────────────────────────────────
    row = {
        "item":   item,
        "qty":    qty,
        "rate":   rate,
        "amount": amount,
        "status": status,
    }

    # Optional text/data fields — only include when non-empty
    optional_str = [
        "product_code", "description", "delivery_product_type",
        "delivery_order_number", "account", "trainers",
    ]
    for k in optional_str:
        v = delivery_order.get(k)
        if v is not None and str(v).strip():
            row[k] = str(v).strip()

    # Optional date fields
    for k in ("start_date", "end_date"):
        v = delivery_order.get(k)
        if v and str(v).strip():
            row[k] = v

    # Optional Link fields (users)
    for k in ("sales_manager", "account_manager", "delivery_person"):
        v = delivery_order.get(k)
        if v and str(v).strip():
            row[k] = v

    # ── Persist ───────────────────────────────────────────────────────
    try:
        doc = frappe.get_doc("PBS Sales Order", sales_order_name)
        doc.append("delivery_orders", row)
        doc.save(ignore_permissions=True)
        frappe.db.commit()
    except frappe.exceptions.ValidationError as e:
        frappe.log_error(
            title="create_delivery_order ValidationError",
            message=frappe.get_traceback(),
        )
        frappe.throw(_("Validation failed while creating Delivery Order: {0}").format(str(e)))
    except Exception as e:
        frappe.log_error(
            title="create_delivery_order Error",
            message=frappe.get_traceback(),
        )
        frappe.throw(_("Could not create Delivery Order: {0}").format(str(e)))

    # Return updated delivery order list
    return frappe.get_all(
        "PBS Delivery Order",
        filters={"parent": sales_order_name, "parenttype": "PBS Sales Order"},
        fields=[
            "name", "product_code", "item", "description",
            "delivery_product_type", "qty", "rate", "amount", "status",
            "start_date", "end_date", "delivery_order_number", "account",
            "sales_manager", "account_manager", "delivery_person", "trainers",
        ],
        order_by="idx asc",
        ignore_permissions=True,
    )
