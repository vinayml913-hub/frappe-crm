import frappe
from frappe import _
from frappe.model.document import Document


class PBSSalesOrder(Document):
    def before_insert(self):
        self.set_gross_profit()
        self.set_final_amount()

    def on_update(self):
        self.set_gross_profit()
        self.set_final_amount()

    def set_gross_profit(self):
        amount        = float(self.amount        or 0)
        total_expense = float(self.total_expense or 0)

        if amount > 0:
            self.gross_profit            = amount - total_expense
            self.gross_profit_percentage = (self.gross_profit / amount) * 100
        elif amount == 0 and total_expense == 0:
            self.gross_profit            = 0
            self.gross_profit_percentage = 0
        else:
            # amount is 0 but there are expenses
            self.gross_profit            = -total_expense
            self.gross_profit_percentage = 0

    def set_final_amount(self):
        amount   = float(self.amount   or 0)
        tax      = float(self.tax      or 0)
        discount = float(self.discount or 0)
        self.final_amount = amount + tax - discount


# ─────────────────────────────────────────────
#  Deal hook — called from hooks.py on_update
# ─────────────────────────────────────────────

def create_sales_order_from_deal(doc, method):
    """
    Sync PBS Sales Order with CRM Deal status changes.

    Rules:
    - Won  → create Sales Order (if none exists) or reactivate a cancelled/archived one
    - Any other status → cancel / archive the linked Sales Order & its Delivery Orders
    """
    try:
        existing = frappe.db.get_value("PBS Sales Order", {"deal": doc.name}, "name")

        if doc.status == "Won":
            if not existing:
                _create_sales_order(doc)
            else:
                # Reactivate if previously suppressed
                current_status = frappe.db.get_value("PBS Sales Order", existing, "status")
                if current_status in ("Cancelled", "Archived"):
                    frappe.db.set_value("PBS Sales Order", existing, "status", "Open")
                    _sync_delivery_orders_status(existing, "Open")
                    frappe.db.commit()
        else:
            if existing:
                if doc.status == "Closed":
                    new_so_status = "Archived"
                    new_do_status = "Cancelled"
                elif doc.status in ("Lost", "Cancelled"):
                    new_so_status = "Cancelled"
                    new_do_status = "Cancelled"
                else:
                    # In Process, Negotiation, Proposal, etc.
                    new_so_status = "Cancelled"
                    new_do_status = "Cancelled"

                frappe.db.set_value("PBS Sales Order", existing, "status", new_so_status)
                _sync_delivery_orders_status(existing, new_do_status)
                frappe.db.commit()

    except Exception:
        frappe.log_error(
            title="create_sales_order_from_deal Error",
            message=frappe.get_traceback(),
        )


# ─────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────

def _create_sales_order(doc):
    """Create a new PBS Sales Order from a Won CRM Deal."""
    try:
        deal_owner = doc.deal_owner or frappe.session.user

        so = frappe.new_doc("PBS Sales Order")
        so.deal            = doc.name
        so.organization    = doc.organization
        so.amount          = float(doc.annual_revenue or doc.deal_value or 0)
        so.sales_manager   = deal_owner
        so.account_manager = deal_owner
        so.status          = "Open"

        # Copy deal products into delivery order rows (if the Deal has a products table)
        products = doc.get("products") or []
        for product in products:
            item_name = (
                getattr(product, "product_name", "") or
                getattr(product, "item_name", "") or ""
            ).strip()
            if not item_name:
                continue

            try:
                qty  = float(getattr(product, "qty",  1) or 1)
                rate = float(getattr(product, "rate", 0) or 0)
            except (TypeError, ValueError):
                qty, rate = 1, 0

            so.append("delivery_orders", {
                "item":        item_name,
                "description": item_name,
                "qty":         qty,
                "rate":        rate,
                "amount":      qty * rate,
                "status":      "Open",   # valid DocType option
            })

        so.insert(ignore_permissions=True)
        frappe.db.commit()

    except Exception:
        frappe.log_error(
            title="Sales Order Creation Failed",
            message=frappe.get_traceback(),
        )


def _sync_delivery_orders_status(sales_order_name, new_status):
    """
    Update the status of all child Delivery Order rows for a given Sales Order.
    Only updates rows that are still active (not already Delivered).
    """
    # Fetch child row names
    rows = frappe.get_all(
        "PBS Delivery Order",
        filters={
            "parent":     sales_order_name,
            "parenttype": "PBS Sales Order",
            "status":     ["not in", ["Delivered"]],
        },
        fields=["name"],
        ignore_permissions=True,
    )

    for row in rows:
        frappe.db.set_value(
            "PBS Delivery Order",
            row["name"],
            "status",
            new_status,
            update_modified=False,
        )
