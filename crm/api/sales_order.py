import frappe
from crm.api.session import get_session_role_flags


@frappe.whitelist()
def get_sales_orders():
	get_session_role_flags()

	session_roles = frappe.get_roles()
	is_admin = "System Manager" in session_roles
	is_manager = "Sales Manager" in session_roles

	if is_admin or is_manager:
		filters = {"status": ["not in", ["Cancelled", "Archived"]]}
		or_filters = None
	else:
		current_user = frappe.session.user
		filters = {"status": ["not in", ["Cancelled", "Archived"]]}
		or_filters = [
			["sales_manager", "=", current_user],
			["account_manager", "=", current_user],
		]

	orders = frappe.get_all(
		"PBS Sales Order",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name", "deal", "organization", "contact_person", "company",
			"email", "phone", "status", "amount", "total_expense",
			"gross_profit", "gross_profit_percentage", "tax", "discount",
			"final_amount", "payment_status", "sales_manager", "account_manager",
			"delivery_manager", "technology", "trainer_assigned", "delivery_type",
			"project_duration", "start_date", "end_date", "delivery_date",
			"lab_required", "training_required", "modified",
		],
		order_by="modified desc",
		ignore_permissions=True,
	)

	for order in orders:
		order["delivery_orders"] = frappe.get_all(
			"PBS Delivery Order",
			filters={"parent": order["name"], "parenttype": "PBS Sales Order"},
			fields=[
				"name", "product_code", "item", "description",
				"delivery_product_type", "qty", "rate", "amount", "status",
				"start_date", "end_date", "delivery_order_number", "account",
				"sales_manager", "account_manager", "delivery_person", "trainers",
			],
			order_by="idx asc",
			ignore_permissions=True,
		)

	return orders


@frappe.whitelist()
def get_sales_order(name):
	get_session_role_flags()
	doc = frappe.get_doc("PBS Sales Order", name)
	return doc.as_dict()


@frappe.whitelist()
def create_delivery_order(sales_order_name, delivery_order):
	import json
	if isinstance(delivery_order, str):
		delivery_order = json.loads(delivery_order)

	doc = frappe.get_doc("PBS Sales Order", sales_order_name)
	doc.append("delivery_orders", delivery_order)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()
