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
            ["sales_manager",    "=", current_user],
            ["account_manager",  "=", current_user],
            ["delivery_manager", "=", current_user],
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
            # Commercial / pricing / costing breakdown - synced from the
            # linked Deal (see pbs_sales_order.py: _map_deal_to_so_fields)
            "currency", "gst_type", "gst_percentage",
            "trainer_costing_type", "trainer_no_of_days", "trainer_no_of_hours",
            "lab_costing_type", "lab_no_of_days", "lab_no_of_hours",
            "lab_pax", "certification_pax",
            "proposed_trainer_commercial", "proposed_lab_cost",
            "proposed_certification_cost", "proposed_misc_expense",
            "proposed_trainer_cost", "proposed_lab_total",
            "proposed_certification_total", "proposed_total", "proposed_total_with_gst",
            "landing_trainer_commercial", "landing_lab_cost",
            "landing_certification_cost", "landing_misc_expense",
            "landing_trainer_cost", "landing_lab_total",
            "landing_certification_total", "landing_total", "landing_total_with_gst",
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
#  SYNC FROM DEAL
# ─────────────────────────────────────────────

@frappe.whitelist()
def resync_sales_order_from_deal(name):
    """
    Re-pull commercial/pricing/costing, delivery configuration, and
    delivery item (Products → Delivery Orders) details from the linked
    Deal onto this Sales Order. Thin proxy so the frontend can call
    everything under crm.api.sales_order.*; the actual logic lives next
    to the doctype in pbs_sales_order.py (shared with the automatic
    on-save sync triggered from CRM Deal).
    """
    from crm.fcrm.doctype.pbs_sales_order.pbs_sales_order import sync_sales_order_from_deal
    return sync_sales_order_from_deal(name)


# ─────────────────────────────────────────────
#  DELETE SALES ORDER
# ─────────────────────────────────────────────

@frappe.whitelist()
def delete_sales_order(name):
    """
    Delete a PBS Sales Order (and its child Delivery Order rows, which
    are removed automatically by Frappe since they're a child table).

    Only System Manager, Sales Manager, or the order's own
    sales_manager / account_manager / delivery_manager may delete it -
    mirrors the visibility rule already used in get_sales_orders().
    """
    session_roles = frappe.get_roles()
    is_admin   = "System Manager" in session_roles
    is_manager = "Sales Manager"  in session_roles

    if not (is_admin or is_manager):
        current_user = frappe.session.user
        owner_fields = frappe.db.get_value(
            "PBS Sales Order",
            name,
            ["sales_manager", "account_manager", "delivery_manager"],
            as_dict=True,
        )
        if not owner_fields or current_user not in (
            owner_fields.sales_manager,
            owner_fields.account_manager,
            owner_fields.delivery_manager,
        ):
            frappe.throw(
                _("You are not allowed to delete this Sales Order"),
                frappe.PermissionError,
            )

    try:
        frappe.delete_doc(
            "PBS Sales Order", name, ignore_permissions=True, force=True
        )
        frappe.db.commit()
    except Exception:
        frappe.log_error(
            title="delete_sales_order Error",
            message=frappe.get_traceback(),
        )
        frappe.throw(_("Could not delete Sales Order {0}").format(name))

    return {"deleted": name}


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


# Statuses where editing is allowed: still in progress / not yet finalized.
# Delivered and Cancelled are terminal states - locking edits there matches
# the existing business rule already encoded in create_sales_order_from_deal's
# Won/Lost/Closed handling (a finalized record shouldn't be silently changed
# after the fact), applied here at the Delivery Order row level instead.
_EDITABLE_DO_STATUSES = {"Open", "In Progress", "On Hold"}
_LOCKED_DO_STATUSES = {"Delivered", "Cancelled"}


@frappe.whitelist()
def update_delivery_order(sales_order_name, delivery_order_name, delivery_order):
    """
    Update an existing PBS Delivery Order child row in place.

    Root cause this fixes: PBS Delivery Order is a child table doctype
    (istable=1, permissions=[]) with no workflow, no is_submittable flag,
    and no status-based locking defined anywhere in its DocType JSON or
    controller. The "can't edit after creation" behaviour reported by
    users was therefore NOT a workflow/permission/backend restriction -
    no such restriction existed in the backend at all. It was a missing
    feature: the frontend never had an edit form for existing rows, and
    no update_delivery_order API existed for it to call. This function
    is that missing piece, with the lock-when-finalized rule implemented
    here (server-side) rather than only in the UI, so the rule can't be
    bypassed by calling the API directly.

    Editable while status is Open / In Progress / On Hold.
    Locked once status is Delivered or Cancelled (terminal states).
    """
    if isinstance(delivery_order, str):
        try:
            delivery_order = json.loads(delivery_order)
        except (json.JSONDecodeError, ValueError) as e:
            frappe.throw(_("Invalid JSON in delivery_order parameter: {0}").format(str(e)))

    if not isinstance(delivery_order, dict):
        frappe.throw(_("delivery_order must be a JSON object / dict"))

    doc = frappe.get_doc("PBS Sales Order", sales_order_name)

    row = None
    for r in doc.delivery_orders:
        if r.name == delivery_order_name:
            row = r
            break

    if row is None:
        frappe.throw(_("Delivery Order {0} not found on Sales Order {1}").format(
            delivery_order_name, sales_order_name
        ))

    current_status = row.status or "Open"
    if current_status in _LOCKED_DO_STATUSES:
        frappe.throw(_(
            "This Delivery Order is {0} and can no longer be edited. "
            "Only Delivery Orders in Open, In Progress, or On Hold status can be modified."
        ).format(current_status))

    # ── Required field validation (same rule as create) ─────────────────
    if "item" in delivery_order:
        item = (delivery_order.get("item") or "").strip()
        if not item:
            frappe.throw(_("Item / Delivery Title is required"))
        row.item = item

    # ── Numeric coercion ──────────────────────────────────────────────────
    qty = row.qty
    if "qty" in delivery_order:
        try:
            qty = float(delivery_order.get("qty") or 1)
            if qty <= 0:
                qty = 1
        except (TypeError, ValueError):
            qty = row.qty
        row.qty = qty

    rate = row.rate
    if "rate" in delivery_order:
        try:
            rate = float(delivery_order.get("rate") or 0)
        except (TypeError, ValueError):
            rate = row.rate
        row.rate = rate

    if "qty" in delivery_order or "rate" in delivery_order:
        row.amount = (row.qty or 0) * (row.rate or 0)

    # ── Status normalisation - moving INTO a locked status is allowed
    #    (that's how a Delivery Order gets finalized in the first place);
    #    moving OUT of a locked status is what's blocked above, before
    #    any of these fields are touched. ─────────────────────────────────
    if "status" in delivery_order:
        raw_status = delivery_order.get("status") or current_status
        new_status = _DO_STATUS_MAP.get(raw_status, raw_status)
        if new_status not in _VALID_DO_STATUSES:
            new_status = current_status
        row.status = new_status

    # ── Optional text/data fields - only overwrite when the key was sent ──
    optional_str = [
        "product_code", "description", "delivery_product_type",
        "delivery_order_number", "account", "trainers",
    ]
    for k in optional_str:
        if k in delivery_order:
            v = delivery_order.get(k)
            setattr(row, k, str(v).strip() if v is not None and str(v).strip() else None)

    # ── Optional date fields ──────────────────────────────────────────────
    for k in ("start_date", "end_date"):
        if k in delivery_order:
            v = delivery_order.get(k)
            setattr(row, k, v if v and str(v).strip() else None)

    # ── Optional Link fields (users / trainer) ────────────────────────────
    for k in ("sales_manager", "account_manager", "delivery_person"):
        if k in delivery_order:
            v = delivery_order.get(k)
            setattr(row, k, v if v and str(v).strip() else None)

    try:
        doc.save(ignore_permissions=True)
        frappe.db.commit()
    except frappe.exceptions.ValidationError as e:
        frappe.log_error(
            title="update_delivery_order ValidationError",
            message=frappe.get_traceback(),
        )
        frappe.throw(_("Validation failed while updating Delivery Order: {0}").format(str(e)))
    except Exception as e:
        frappe.log_error(
            title="update_delivery_order Error",
            message=frappe.get_traceback(),
        )
        frappe.throw(_("Could not update Delivery Order: {0}").format(str(e)))

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


# ─────────────────────────────────────────────
#  HELPERS FOR FRONTEND DROPDOWNS
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_crm_users():
    """
    Return all active users that have at least one CRM-related role.
    Returns list of {value: email, label: "Full Name (email)"} for dropdowns.
    """
    users = frappe.get_all(
        "User",
        filters={
            "enabled": 1,
            "user_type": "System User",
            "name": ["not in", ["Administrator", "Guest"]],
        },
        fields=["name", "full_name", "user_image"],
        order_by="full_name asc",
        ignore_permissions=True,
    )

    return [
        {
            "value": u["name"],          # email — the actual Link field value
            "label": u["full_name"] or u["name"],
            "image": u.get("user_image") or "",
        }
        for u in users
    ]
