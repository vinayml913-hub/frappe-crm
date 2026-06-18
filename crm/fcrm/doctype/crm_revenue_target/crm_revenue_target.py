import frappe
from frappe import _
from frappe.model.document import Document


class CRMRevenueTarget(Document):
    def autoname(self):
        self._set_period_label()
        user_part = (self.user or "user").split("@")[0]
        self.name = f"RT-{user_part}-{self.period_type}-{self.period_label}"

    def validate(self):
        self._set_period_label()
        self._validate_period_fields()
        self._validate_duplicate()
        self._validate_amount()

    def _set_period_label(self):
        """Build a human-readable, sortable period label."""
        if not self.year:
            return

        if self.period_type == "Monthly" and self.month:
            self.period_label = f"{self.year}-{int(self.month):02d}"
        elif self.period_type == "Quarterly" and self.quarter:
            self.period_label = f"{self.year}-{self.quarter}"
        elif self.period_type == "Yearly":
            self.period_label = f"{self.year}"

    def _validate_period_fields(self):
        if self.period_type == "Monthly" and not self.month:
            frappe.throw(_("Month is required for a Monthly target"))
        if self.period_type == "Quarterly" and not self.quarter:
            frappe.throw(_("Quarter is required for a Quarterly target"))
        if not self.year:
            frappe.throw(_("Year is required"))

    def _validate_duplicate(self):
        """Prevent two targets for the same user + period."""
        filters = {
            "user": self.user,
            "period_type": self.period_type,
            "year": self.year,
            "name": ["!=", self.name],
        }
        if self.period_type == "Monthly":
            filters["month"] = self.month
        elif self.period_type == "Quarterly":
            filters["quarter"] = self.quarter

        if frappe.db.exists("CRM Revenue Target", filters):
            frappe.throw(
                _("A {0} revenue target already exists for {1} in {2}").format(
                    self.period_type, self.user, self.period_label
                )
            )

    def _validate_amount(self):
        try:
            amount = float(self.target_amount or 0)
        except (TypeError, ValueError):
            frappe.throw(_("Target Amount must be a number"))
        if amount < 0:
            frappe.throw(_("Target Amount cannot be negative"))
