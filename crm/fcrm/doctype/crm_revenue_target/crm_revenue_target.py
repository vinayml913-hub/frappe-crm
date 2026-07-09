import frappe
from frappe import _
from frappe.model.document import Document


class CRMRevenueTarget(Document):
	def validate(self):
		self.prevent_duplicate_target()
		if not self.created_by_user:
			self.created_by_user = frappe.session.user

	def prevent_duplicate_target(self):
		"""Prevent duplicate Employee + Period + Year targets."""
		filters = {
			"employee": self.employee,
			"target_type": self.target_type,
			"year": self.year,
			"name": ["!=", self.name],
		}
		if self.target_type == "Monthly":
			filters["month"] = self.month
		elif self.target_type == "Quarterly":
			filters["quarter"] = self.quarter

		if frappe.db.exists("CRM Revenue Target", filters):
			frappe.throw(
				_("A {0} target for {1} in {2} already exists").format(
					self.target_type, self.employee, self.year
				)
			)
