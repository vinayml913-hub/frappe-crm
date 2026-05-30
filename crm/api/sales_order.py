import frappe
from crm.api.session import get_session_role_flags


@frappe.whitelist()
def get_sales_orders():
	get_session_role_flags()

	session_roles = frappe.get_roles()
	is_admin = "System Manager" in session_roles
	is_manager = "Sales Manager" in session_roles

	if is_admin or is_manager:
		filters = {}
		or_filters = None
	else:
		current_user = frappe.session.user
		filters = {}
		or_filters = [
			["sales_manager", "=", current_user],
			["account_manager", "=", current_user],
		]

	orders = frappe.get_all(
		"PBS Sales Order",
		filters=filters,
		or_filters=or_filters,
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
