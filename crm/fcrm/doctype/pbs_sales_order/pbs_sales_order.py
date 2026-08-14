import frappe
from frappe import _
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


def _first_solution_manager(deal_doc):
	for row in deal_doc.get("solution_managers") or []:
		if row.get("user"):
			return row.get("user")
	return None


def _map_deal_to_so_fields(so, deal_doc):
	"""
	Copy every commercial / pricing / costing / delivery-configuration
	field that matters from a CRM Deal onto a PBS Sales Order. Used both
	when the Sales Order is first auto-created (Deal marked Won) and
	whenever the linked Deal is saved again afterwards, so later edits on
	the Deal (a corrected Landing Cost, a GST toggle, a new Trainer, a
	changed Solution Manager, ...) keep flowing into the Sales Order
	instead of it being stuck with whatever was true the moment it was
	created.

	Fields the Sales Order owns and can diverge from the Deal after
	creation - amount, total_expense, tax, discount, final_amount,
	gross_profit, gross_profit_percentage, status, payment_status - are
	NOT touched here. Those are the Sales Order's own billing figures
	(may be negotiated, part-paid, etc. after the Deal is won) and are
	only ever seeded once, at creation, in create_sales_order_from_deal.
	"""
	so.organization = deal_doc.organization
	so.contact_person = deal_doc.contact
	so.email = deal_doc.email or so.email or ""
	so.phone = deal_doc.mobile_no or deal_doc.phone or so.phone or ""
	so.company = deal_doc.organization_name or so.company or ""

	# Project / delivery configuration
	so.training_name = deal_doc.get("deal_name") or ""
	so.technology = deal_doc.get("technology") or ""
	so.delivery_type = deal_doc.get("delivery_type") or ""
	so.project_duration = deal_doc.get("duration") or ""
	so.start_date = deal_doc.get("start_date") or None
	so.end_date = deal_doc.get("end_date") or None
	so.delivery_date = deal_doc.get("delivery_date") or deal_doc.get("expected_close_date") or None
	so.trainer_assigned = deal_doc.get("trainer") or None

	# Team
	first_solution_manager = _first_solution_manager(deal_doc)
	so.sales_manager = (
		deal_doc.get("sales_manager") or deal_doc.deal_owner or so.sales_manager or frappe.session.user
	)
	so.account_manager = (
		first_solution_manager or deal_doc.deal_owner or so.account_manager or frappe.session.user
	)
	so.delivery_manager = deal_doc.get("training_engagement_manager") or so.delivery_manager or None

	# ── Commercial / Pricing / Costing breakdown ────────────────────────
	# Read-only snapshot of the Deal's Proposed-vs-Landing costing model
	# (see CRM Deal.calculate_financials). Kept in sync so the Sales
	# Order always shows exactly what was quoted vs. what it actually
	# cost, without re-implementing the calculation a second time here -
	# the Deal remains the single source of truth for these numbers.
	so.currency = deal_doc.get("currency") or so.currency

	so.trainer_costing_type = deal_doc.get("trainer_costing_type") or ""
	so.trainer_no_of_days = deal_doc.get("trainer_no_of_days") or 0
	so.trainer_no_of_hours = deal_doc.get("trainer_no_of_hours") or 0
	so.lab_costing_type = deal_doc.get("lab_costing_type") or ""
	so.lab_no_of_days = deal_doc.get("lab_no_of_days") or 0
	so.lab_no_of_hours = deal_doc.get("lab_no_of_hours") or 0
	so.lab_pax = deal_doc.get("lab_pax") or 0
	so.certification_pax = deal_doc.get("certification_pax") or 0

	so.proposed_trainer_commercial = deal_doc.get("proposed_trainer_commercial") or 0
	so.proposed_lab_cost = deal_doc.get("proposed_lab_cost") or 0
	so.proposed_certification_cost = deal_doc.get("proposed_certification_cost") or 0
	so.proposed_misc_expense = deal_doc.get("proposed_misc_expense") or 0
	so.proposed_trainer_cost = deal_doc.get("proposed_trainer_cost") or 0
	so.proposed_lab_total = deal_doc.get("proposed_lab_total") or 0
	so.proposed_certification_total = deal_doc.get("proposed_certification_total") or 0
	so.proposed_total = deal_doc.get("proposed_total") or 0

	so.landing_trainer_commercial = deal_doc.get("landing_trainer_commercial") or 0
	so.landing_lab_cost = deal_doc.get("landing_lab_cost") or 0
	so.landing_certification_cost = deal_doc.get("landing_certification_cost") or 0
	so.landing_misc_expense = deal_doc.get("landing_misc_expense") or 0
	so.landing_trainer_cost = deal_doc.get("landing_trainer_cost") or 0
	so.landing_lab_total = deal_doc.get("landing_lab_total") or 0
	so.landing_certification_total = deal_doc.get("landing_certification_total") or 0
	so.landing_total = deal_doc.get("landing_total") or 0

	so.gst_type = deal_doc.get("gst_type") or ""
	so.gst_percentage = deal_doc.get("gst_percentage") or 0
	so.proposed_total_with_gst = deal_doc.get("proposed_total_with_gst") or 0
	so.landing_total_with_gst = deal_doc.get("landing_total_with_gst") or 0


def _sync_delivery_items_from_deal(so, deal_doc):
	"""
	Sync the Deal's Products table into the Sales Order's Delivery Orders
	table. Matched on product_code (falling back to product name) so:
	  - a product already represented as a Delivery Order row is UPDATED
	    in place (qty / rate / amount) instead of being duplicated,
	  - a new product added to the Deal gets appended as a new row,
	  - Delivery Order rows added manually (no matching Deal product)
	    are left untouched.
	Returns True if at least one row came from the Deal's Products table,
	so the caller knows whether the training-summary fallback row is
	still needed.
	"""
	products = deal_doc.get("products") or []
	if not products:
		return False

	existing_by_key = {}
	for row in so.delivery_orders:
		key = row.product_code or row.item
		if key:
			existing_by_key[key] = row

	for p in products:
		key = p.get("product_code") or p.get("product_name")
		if not key:
			continue

		qty = float(p.get("qty") or 1)
		rate = float(p.get("rate") or 0)
		amount = float(p.get("net_amount") or p.get("amount") or (qty * rate))

		row = existing_by_key.get(key)
		if row:
			row.qty = qty
			row.rate = rate
			row.amount = amount
			if not row.item:
				row.item = p.get("product_name") or key
		else:
			new_row = so.append(
				"delivery_orders",
				{
					"product_code": p.get("product_code") or "",
					"item": p.get("product_name") or key,
					"description": deal_doc.get("technology") or "",
					"delivery_product_type": "Product",
					"qty": qty,
					"rate": rate,
					"amount": amount,
					"status": "Open",
					"start_date": deal_doc.get("start_date") or None,
					"end_date": deal_doc.get("end_date") or None,
					"account": deal_doc.organization_name or "",
					"sales_manager": so.sales_manager,
					"account_manager": so.account_manager,
					"delivery_person": so.delivery_manager,
				},
			)
			existing_by_key[key] = new_row

	return True


def create_sales_order_from_deal(doc, method):
	"""
	Auto-create the PBS Sales Order when a Deal is marked Won, and - since
	this also runs on every later save of the Deal (see hooks.py) - keep
	an already-created Sales Order's commercial/pricing/costing and
	delivery item details in sync with the Deal from then on.
	"""
	if doc.status != "Won":
		return

	existing_name = frappe.db.exists("PBS Sales Order", {"deal": doc.name})

	try:
		if existing_name:
			# Deal was already Won and a Sales Order exists - re-sync the
			# fields that should always mirror the Deal (this is what
			# makes later Deal edits show up on the Sales Order).
			so = frappe.get_doc("PBS Sales Order", existing_name)
			_map_deal_to_so_fields(so, doc)
			_sync_delivery_items_from_deal(so, doc)
			so.save(ignore_permissions=True)
			frappe.db.commit()
			return

		so = frappe.new_doc("PBS Sales Order")
		so.deal = doc.name
		_map_deal_to_so_fields(so, doc)

		# Financial Info — from Deal's Proposed/Landing commercial model.
		# "amount" (what's billed to the client) = Proposed Total, GST as
		# selected on the Deal; "total_expense" (actual cost) = Landing Total.
		# These are seeded once here and become the Sales Order's own
		# figures from this point on (see _map_deal_to_so_fields docstring).
		so.amount = doc.get("proposed_total_with_gst") or doc.get("proposed_total") or 0
		so.total_expense = doc.get("landing_total") or 0
		so.tax = 0
		so.discount = 0

		so.notes = doc.get("notes") or ""
		so.status = "Open"
		so.payment_status = "Pending"

		# ---- Delivery Items: one row per Deal Product, synced in ----
		has_product_rows = _sync_delivery_items_from_deal(so, doc)

		# Fallback: no Products table used on the Deal (training-only,
		# quoted purely via the costing breakdown) - keep the original
		# single "Training Delivery" summary row so every Sales Order
		# still gets at least one Delivery Order to work from.
		if not has_product_rows:
			trainer_name = ""
			if doc.get("trainer"):
				trainer_name = (
					frappe.db.get_value("CRM Trainer", doc.get("trainer"), "trainer_name")
					or doc.get("trainer")
				)

			so.append(
				"delivery_orders",
				{
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
				},
			)

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

	except Exception:
		frappe.log_error(
			title="Sales Order Creation/Sync Failed",
			message=frappe.get_traceback()
		)


@frappe.whitelist()
def sync_sales_order_from_deal(name):
	"""
	Manually re-pull commercial/pricing/costing, delivery configuration,
	and delivery item details from the linked Deal onto an existing Sales
	Order. Useful for backfilling Sales Orders that were created before
	this sync existed, or to force a refresh on demand.
	"""
	so = frappe.get_doc("PBS Sales Order", name)
	if not so.deal:
		frappe.throw(_("This Sales Order is not linked to a Deal"))

	deal_doc = frappe.get_doc("CRM Deal", so.deal)
	_map_deal_to_so_fields(so, deal_doc)
	_sync_delivery_items_from_deal(so, deal_doc)

	try:
		so.save(ignore_permissions=True)
		frappe.db.commit()
	except frappe.exceptions.ValidationError as e:
		frappe.log_error(
			title="sync_sales_order_from_deal ValidationError",
			message=frappe.get_traceback(),
		)
		frappe.throw(_("Validation failed while syncing from Deal: {0}").format(str(e)))

	return so.as_dict()


@frappe.whitelist()
def get_sales_orders():
	return frappe.get_all(
		"PBS Sales Order",
		fields=[
			"name", "organization", "status", "amount",
			"gross_profit", "gross_profit_percentage", "deal",
			"sales_manager", "account_manager", "training_name", "technology",
			"trainer_assigned", "start_date", "end_date",
			"payment_status", "delivery_type", "delivery_manager"
		],
		order_by="modified desc"
	)
