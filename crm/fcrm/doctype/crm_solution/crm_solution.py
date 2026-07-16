# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CRMSolution(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		availability_for_discussion_call: DF.Data | None
		availability_for_training: DF.Data | None
		costing_for_training: DF.Currency
		costing_type: DF.Literal["Per Day", "Per Hour"]
		duration: DF.Data | None
		lab_cost: DF.Currency
		location: DF.Data | None
		reference_docname: DF.DynamicLink | None
		reference_doctype: DF.Link | None
		sm: DF.Link | None
		trainer: DF.Link | None
		trainer_experience: DF.Data | None
		trainer_name: DF.Data
	# end: auto-generated types

	@staticmethod
	def default_list_data():
		rows = [
			"name",
			"trainer_name",
			"trainer_experience",
			"costing_for_training",
			"lab_cost",
			"duration",
			"availability_for_training",
			"availability_for_discussion_call",
			"location",
			"sm",
			"reference_doctype",
			"reference_docname",
			"owner",
			"modified",
		]
		return {"columns": [], "rows": rows}
