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
		amount = float(self.amount or 0)
		tax = float(self.tax or 0)
		discount = float(self.discount or 0)
		self.final_amount = amount + tax - discount


def create_sales_order_from_deal(doc, method):
	"""Sync Sales Order with Deal status changes"""

	existing = frappe.db.get_value("PBS Sales Order", {"deal": doc.name}, "name")

	if doc.status == "Won":
		if not existing:
			_create_sales_order(doc)
		else:
			# Reactivate if cancelled/archived
			current_status = frappe.db.get_value("PBS Sales Order", existing, "status")
			if current_status in ("Cancelled", "Archived"):
				frappe.db.set_value("PBS Sales Order", existing, "status", "Open")
				frappe.db.commit()
	else:
		if existing:
			if doc.status == "Closed":
				new_status = "Archived"
			elif doc.status in ("Lost", "Cancelled"):
				new_status = "Cancelled"
			else:
				# In Process, Negotiation, Proposal etc
				new_status = "Cancelled"

			frappe.db.set_value("PBS Sales Order", existing, "status", new_status)
			frappe.db.commit()


def _create_sales_order(doc):
	"""Internal: Create Sales Order from Won deal"""
	try:
		deal_owner = doc.deal_owner or frappe.session.user

		sales_order = frappe.new_doc("PBS Sales Order")
		sales_order.deal = doc.name
		sales_order.organization = doc.organization
		sales_order.amount = float(doc.annual_revenue or doc.deal_value or 0)
		sales_order.sales_manager = deal_owner
		sales_order.account_manager = deal_owner
		sales_order.status = "Open"

		# Copy products from deal into delivery orders
		if doc.get("products"):
			for product in doc.products:
				item_name = getattr(product, 'product_name', '') or getattr(product, 'item_name', '') or ''
				if not item_name:
					continue
				qty = float(getattr(product, 'qty', 1) or 1)
				rate = float(getattr(product, 'rate', 0) or 0)
				sales_order.append("delivery_orders", {
					"item": item_name,
					"description": item_name,
					"qty": qty,
					"rate": rate,
					"amount": qty * rate,
					"status": "Pending",
				})

		sales_order.insert(ignore_permissions=True)
		frappe.db.commit()

	except Exception:
		frappe.log_error(
			title="Sales Order Creation Failed",
			message=frappe.get_traceback()
		)
