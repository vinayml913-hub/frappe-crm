import frappe
from frappe.model.document import Document


class PBSSalesOrder(Document):
	def before_insert(self):
		self.set_gross_profit()
		self.set_final_amount()

	def on_update(self):
		self.set_gross_profit()
		self.set_final_amount()

	def set_gross_profit(self):
		if self.amount and self.total_expense:
			self.gross_profit = self.amount - self.total_expense
			if self.amount > 0:
				self.gross_profit_percentage = (self.gross_profit / self.amount) * 100
			else:
				self.gross_profit_percentage = 0

	def set_final_amount(self):
		amount = self.amount or 0
		tax = self.tax or 0
		discount = self.discount or 0
		self.final_amount = amount + tax - discount


def sync_sales_order_with_deal(doc, method):
	"""Sync Sales Order status when Deal status changes"""
	existing = frappe.db.exists("PBS Sales Order", {"deal": doc.name})

	if doc.status == "Won":
		if not existing:
			_create_sales_order(doc)
		else:
			so = frappe.get_doc("PBS Sales Order", existing)
			if so.status in ("Cancelled", "Archived"):
				so.status = "Open"
				so.save(ignore_permissions=True)
				frappe.db.commit()
	elif doc.status == "Lost":
		if existing:
			frappe.db.set_value("PBS Sales Order", existing, "status", "Cancelled")
			frappe.db.commit()
	elif doc.status == "Closed":
		if existing:
			frappe.db.set_value("PBS Sales Order", existing, "status", "Archived")
			frappe.db.commit()
	elif doc.status in ("In Process", "Negotiation", "Proposal/Quotation", "Demo/Making", "Qualification"):
		if existing:
			frappe.db.set_value("PBS Sales Order", existing, "status", "Cancelled")
			frappe.db.commit()


def _create_sales_order(doc):
	try:
		deal_owner = doc.deal_owner or frappe.session.user

		sales_order = frappe.new_doc("PBS Sales Order")
		sales_order.deal = doc.name
		sales_order.organization = doc.organization
		sales_order.amount = doc.annual_revenue or doc.deal_value or 0
		sales_order.sales_manager = deal_owner
		sales_order.account_manager = deal_owner
		sales_order.status = "Open"

		if doc.get("products"):
			for product in doc.products:
				sales_order.append("delivery_orders", {
					"item": product.product_name or "",
					"description": product.product_name or "",
					"qty": product.qty or 1,
					"rate": product.rate or 0,
					"amount": product.amount or (product.qty or 1) * (product.rate or 0),
					"status": "Pending",
				})

		sales_order.insert(ignore_permissions=True)
		frappe.db.commit()

	except Exception:
		frappe.log_error(
			title="Sales Order Creation Failed",
			message=frappe.get_traceback()
		)


def create_sales_order_from_deal(doc, method):
	sync_sales_order_with_deal(doc, method)
