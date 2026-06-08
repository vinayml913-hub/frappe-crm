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
		elif self.amount and not self.total_expense:
			self.gross_profit = self.amount
			self.gross_profit_percentage = 100


def create_sales_order_from_deal(doc, method):
	"""Auto create PBS Sales Order when Deal status = Won"""
	if doc.status != "Won":
		return

	existing = frappe.db.exists("PBS Sales Order", {"deal": doc.name})
	if existing:
		return

	try:
		sales_order = frappe.new_doc("PBS Sales Order")
		sales_order.deal = doc.name
		sales_order.organization = doc.organization
		sales_order.contact_person = doc.contact

		# Pull financial fields from new Deal Details tab
		sales_order.amount = doc.get("amount") or doc.deal_value or doc.net_total or 0
		sales_order.total_expense = doc.get("expense") or 0

		# Pull team fields from Deal
		sales_order.sales_manager = doc.get("sales_manager") or doc.deal_owner or frappe.session.user
		sales_order.account_manager = doc.get("account_manager") or doc.deal_owner or frappe.session.user

		# Pull delivery/lab fields
		sales_order.lab_required = doc.get("lab_required") or 0
		sales_order.training_required = doc.get("training_required") or 0
		sales_order.delivery_date = doc.get("expected_close_date") or doc.expected_closure_date

		# Pull notes
		sales_order.notes = doc.get("accounting_notes") or ""

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


@frappe.whitelist()
def get_sales_orders():
	"""Get sales orders based on user role"""
	roles = frappe.get_roles(frappe.session.user)

	return frappe.get_all(
		"PBS Sales Order",
		fields=[
			"name", "organization", "status", "amount",
			"gross_profit", "gross_profit_percentage", "deal"
		],
		order_by="modified desc"
	)
