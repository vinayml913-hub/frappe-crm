import frappe
from frappe.model.document import Document


class PBSSalesOrder(Document):
	def before_insert(self):
		self.set_gross_profit()

	def on_update(self):
		self.set_gross_profit()

	def set_gross_profit(self):
		if self.amount and self.total_expense:
			self.gross_profit = self.amount - self.total_expense
			if self.amount > 0:
				self.gross_profit_percentage = (self.gross_profit / self.amount) * 100
			else:
				self.gross_profit_percentage = 0


def create_sales_order_from_deal(doc, method):
	"""Auto create Sales Order when Deal is Won"""
	if doc.status != "Won":
		return

	existing = frappe.db.exists("PBS Sales Order", {"deal": doc.name})
	if existing:
		return

	try:
		deal_owner = doc.deal_owner or frappe.session.user

		sales_order = frappe.new_doc("PBS Sales Order")
		sales_order.deal = doc.name
		sales_order.organization = doc.organization
		sales_order.amount = doc.deal_value or doc.net_total or 0
		sales_order.sales_manager = deal_owner
		sales_order.account_manager = deal_owner
		sales_order.contact_person = doc.contact
		sales_order.status = "Open"
		sales_order.insert(ignore_permissions=True)
		frappe.db.commit()
		frappe.msgprint(
			f"Sales Order {sales_order.name} created successfully!",
			alert=True
		)
	except Exception as e:
		frappe.log_error(
			title="Sales Order Creation Failed",
			message=frappe.get_traceback()
		)