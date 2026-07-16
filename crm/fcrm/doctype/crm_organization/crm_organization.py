# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from crm.api.exchange_rate import get_exchange_rate
from crm.utils.permissions import owner_only_has_permission, owner_only_query_conditions

# Record-level access to CRM Organization ("Client" in the sidebar) is
# strict "creator only", same rule as CRM Deal - see
# crm.utils.permissions. Only System Manager/Administrator bypass this.


def has_permission(doc, ptype=None, user=None):
	"""A CRM Organization is visible only to the user who created it, or
	to a System Manager/Administrator."""
	return owner_only_has_permission(doc, ptype=ptype, user=user)


def get_permission_query_conditions(user=None):
	"""List/kanban/report view counterpart to has_permission() above."""
	return owner_only_query_conditions("CRM Organization", user=user)


class CRMOrganization(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.Link | None
		annual_revenue: DF.Currency
		currency: DF.Link | None
		exchange_rate: DF.Float
		industry: DF.Link | None
		no_of_employees: DF.Literal["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
		organization_logo: DF.AttachImage | None
		organization_name: DF.Data | None
		territory: DF.Link | None
		website: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.update_exchange_rate()

	def update_exchange_rate(self):
		if self.has_value_changed("currency") or not self.exchange_rate:
			system_currency = frappe.db.get_single_value("FCRM Settings", "currency") or "USD"
			exchange_rate = 1
			if self.currency and self.currency != system_currency:
				exchange_rate = get_exchange_rate(self.currency, system_currency)

			self.db_set("exchange_rate", exchange_rate)

	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Organization",
				"type": "Data",
				"key": "organization_name",
				"width": "16rem",
			},
			{
				"label": "Website",
				"type": "Data",
				"key": "website",
				"width": "14rem",
			},
			{
				"label": "Industry",
				"type": "Link",
				"key": "industry",
				"options": "CRM Industry",
				"width": "14rem",
			},
			{
				"label": "Annual Revenue",
				"type": "Currency",
				"key": "annual_revenue",
				"width": "14rem",
			},
			{
				"label": "Last Modified",
				"type": "Datetime",
				"key": "modified",
				"width": "8rem",
			},
		]
		rows = [
			"name",
			"organization_name",
			"organization_logo",
			"website",
			"industry",
			"currency",
			"annual_revenue",
			"modified",
		]
		return {"columns": columns, "rows": rows}
