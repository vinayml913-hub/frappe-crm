import frappe
from frappe.model.document import Document


class PBSSalesOrder(Document):
	def before_insert(self):
		self.set_financials()

	def on_update(self):
		self.set_financials()

	def set_financials(self):
		amount = float(self.amount or 0)
		expense = float(self.total_expense or 0)
		tax = float(self.tax or 0)
		discount = float(self.discount or 0)

		if amount > 0:
			self.gross_profit = amount - expense
			self.gross_profit_percentage = (self.gross_profit / amount) * 100
		else:
			self.gross_profit = 0
			self.gross_profit_percentage = 0

		self.final_amount = amount + tax - discount


def create_sales_order_from_deal(doc, method):
	"""Auto create PBS Sales Order when Deal status = Won"""
	if doc.status != "Won":
		return

	existing = frappe.db.exists("PBS Sales Order", {"deal": doc.name})
	if existing:
		return

	try:
		so = frappe.new_doc("PBS Sales Order")

		# Basic Info
		so.deal = doc.name
		so.organization = doc.organization
		so.contact_person = doc.contact
		so.email = doc.email or ""
		so.phone = doc.mobile_no or doc.phone or ""
		so.company = doc.organization_name or ""

		# Financial Info — from Deal final calculation
		so.amount = doc.get("final_amount") or doc.get("base_amount") or 0
		so.total_expense = doc.get("total_expense") or 0
		so.tax = 0
		so.discount = 0

		# Project Info
		so.technology = doc.get("technology") or ""
		so.delivery_type = doc.get("delivery_type") or ""
		so.project_duration = doc.get("duration") or ""
		so.start_date = doc.get("start_date") or None
		so.end_date = doc.get("end_date") or None
		so.delivery_date = doc.get("delivery_date") or doc.get("expected_close_date") or None

		# Trainer Info
		so.trainer_assigned = doc.get("trainer") or None

		# Team Info
		so.sales_manager = doc.get("sales_manager") or doc.deal_owner or frappe.session.user
		so.account_manager = doc.get("account_manager") or doc.deal_owner or frappe.session.user
		so.delivery_manager = doc.get("training_engagement_manager") or None

		# Other
		so.lab_required = doc.get("lab_required") or 0
		so.training_required = doc.get("training_required") or 0
		so.notes = doc.get("accounting_notes") or ""
		so.status = "Open"
		so.payment_status = "Pending"

		so.insert(ignore_permissions=True)
		frappe.db.commit()

		frappe.msgprint(
			f"Sales Order {so.name} created successfully!",
			alert=True
		)

	except Exception as e:
		frappe.log_error(
			title="Sales Order Creation Failed",
			message=frappe.get_traceback()
		)


@frappe.whitelist()
def get_sales_orders():
	return frappe.get_all(
		"PBS Sales Order",
		fields=[
			"name", "organization", "status", "amount",
			"gross_profit", "gross_profit_percentage", "deal",
			"sales_manager", "account_manager", "technology",
			"trainer_assigned", "start_date", "end_date",
			"payment_status", "delivery_type"
		],
		order_by="modified desc"
	)
