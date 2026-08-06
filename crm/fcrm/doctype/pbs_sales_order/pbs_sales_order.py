import frappe
from frappe.model.document import Document


class PBSSalesOrder(Document):
	def before_insert(self):
		self.set_financials()

	def on_update(self):
		self.set_financials()
		self.share_with_assigned_users()

	def after_insert(self):
		self.share_with_assigned_users()

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

	def share_with_assigned_users(self):
		"""
		Auto-share this Sales Order (and its Delivery Orders, which are
		a child table on the same doc) with the specific users assigned
		as Sales Manager, Solution Manager (account_manager), and
		Training Engagement Co-ordinator (delivery_manager) -
		regardless of their role.
		"""
		users_to_share = set(
			filter(None, [self.sales_manager, self.account_manager, self.delivery_manager])
		)

		if not users_to_share:
			return

		existing_shares = frappe.get_all(
			"DocShare",
			filters={"share_doctype": self.doctype, "share_name": self.name},
			pluck="user",
		)

		for user in users_to_share:
			if user in existing_shares:
				continue
			try:
				frappe.share.add_docshare(
					self.doctype,
					self.name,
					user,
					read=1,
					write=1,
					flags={"ignore_share_permission": True},
				)
			except Exception:
				frappe.log_error(
					title="PBS Sales Order Auto-Share Failed",
					message=frappe.get_traceback(),
				)


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

		# Financial Info — from Deal's Proposed/Landing commercial model.
		# "amount" (what's billed to the client) = Proposed Total, GST as
		# selected on the Deal; "total_expense" (actual cost) = Landing Total.
		so.amount = doc.get("proposed_total_with_gst") or doc.get("proposed_total") or 0
		so.total_expense = doc.get("landing_total") or 0
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
		# solution_managers = "Solution Manager" on Deal - now a multi-select
		# child table; PBS Sales Order still only carries a single Solution
		# Manager, so we take the first row (the rest remain visible on the
		# Deal itself for reporting/target purposes).
		# delivery_manager = "Training Engagement Co-ordinator" on Deal
		first_solution_manager = None
		for row in doc.get("solution_managers") or []:
			if row.get("user"):
				first_solution_manager = row.get("user")
				break

		so.sales_manager = doc.get("sales_manager") or doc.deal_owner or frappe.session.user
		so.account_manager = first_solution_manager or doc.deal_owner or frappe.session.user
		so.delivery_manager = doc.get("training_engagement_manager") or None

		# Other
		# Lab Required / Training Required were removed from Deal - leave
		# unset here (they can still be set manually on the Sales Order).
		so.notes = doc.get("notes") or ""
		so.status = "Open"
		so.payment_status = "Pending"

		# ---- Auto-create one Delivery Order row from Deal's Project Info ----
		trainer_name = ""
		if doc.get("trainer"):
			trainer_name = frappe.db.get_value("CRM Trainer", doc.get("trainer"), "trainer_name") or doc.get("trainer")

		delivery_row = {
			"item": doc.get("technology") or "Training Delivery",
			"description": f"Duration: {doc.get('duration') or ''}".strip(),
			"delivery_product_type": "Training",
			"qty": 1,
			"rate": so.amount or 0,
			"status": "Open",
			"start_date": doc.get("start_date") or None,
			"end_date": doc.get("end_date") or None,
			"account": doc.organization_name or "",
			"sales_manager": so.sales_manager,
			"account_manager": so.account_manager,
			"delivery_person": so.delivery_manager,
			"trainers": trainer_name,
		}
		so.append("delivery_orders", delivery_row)

		so.insert(ignore_permissions=True)
		frappe.db.commit()

		# Explicitly share right after insert too, in case after_insert
		# ran before all team fields were committed
		so.share_with_assigned_users()
		frappe.db.commit()

		frappe.msgprint(
			f"Sales Order {so.name} created successfully with Delivery Order!",
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
			"payment_status", "delivery_type", "delivery_manager"
		],
		order_by="modified desc"
	)
