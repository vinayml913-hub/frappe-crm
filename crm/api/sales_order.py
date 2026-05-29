import frappe
from crm.api.session import get_session_role_flags


@frappe.whitelist()
def get_sales_orders():
	get_session_role_flags()

	filters = {}
	session_roles = frappe.get_roles()

	# Sales User / Solution Manager can only see their own orders
	if "System Manager" not in session_roles and "Sales Manager" not in session_roles:
		filters["sales_manager"] = frappe.session.user

	orders = frappe.get_all(
		"PBS Sales Order",
		filters=filters,
		fields=[
			"name",
			"deal",
			"organization",
			"contact_person",
			"status",
			"amount",
			"total_expense",
			"gross_profit",
			"gross_profit_percentage",
			"sales_manager",
			"account_manager",
			"delivery_date",
			"lab_required",
			"training_required",
			"modified",
		],
		order_by="modified desc",
	)

	# Attach delivery orders for each sales order
	for order in orders:
		order["delivery_orders"] = frappe.get_all(
			"PBS Delivery Order",
			filters={"parent": order["name"], "parenttype": "PBS Sales Order"},
			fields=["item", "description", "qty", "rate", "amount", "delivery_date", "status"],
			order_by="idx asc",
		)

	return orders


@frappe.whitelist()
def get_sales_order(name):
	get_session_role_flags()
	doc = frappe.get_doc("PBS Sales Order", name)
	return doc.as_dict()
