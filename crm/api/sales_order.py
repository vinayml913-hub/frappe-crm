import frappe
from crm.api.session import get_session_role_flags


@frappe.whitelist()
def get_sales_orders():
	get_session_role_flags()

	session_roles = frappe.get_roles()
	is_admin = "System Manager" in session_roles
	is_manager = "Sales Manager" in session_roles
	is_sales_user = "Sales User" in session_roles
	is_solution_manager = "Solution Manager" in session_roles

	# Build filters based on role
	if is_admin or is_manager:
		# Admin and Manager see ALL orders
		filters = {}
	else:
		# Sales User and Solution Manager see only their own
		# Match by sales_manager OR deal_owner
		current_user = frappe.session.user
		filters = [
			["PBS Sales Order", "sales_manager", "=", current_user]
		]

	orders = frappe.get_all(
		"PBS Sales Order",
		filters=filters if isinstance(filters, dict) else None,
		or_filters=filters if isinstance(filters, list) else None,
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
		ignore_permissions=True,
	)

	# Attach delivery orders for each sales order
	for order in orders:
		order["delivery_orders"] = frappe.get_all(
			"PBS Delivery Order",
			filters={"parent": order["name"], "parenttype": "PBS Sales Order"},
			fields=["item", "description", "qty", "rate", "amount", "delivery_date", "status"],
			order_by="idx asc",
			ignore_permissions=True,
		)

	return orders


@frappe.whitelist()
def get_sales_order(name):
	get_session_role_flags()
	doc = frappe.get_doc("PBS Sales Order", name)
	return doc.as_dict()
