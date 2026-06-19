import frappe
from frappe.model.document import Document


class CRMTrainerImportLog(Document):
	"""
	Read-mostly audit record written by crm.api.trainers_import.commit_import.
	No custom validation needed beyond standard Frappe field types -
	this doctype exists purely to satisfy the "Import History" requirement
	(file name, imported by, timestamp, counts, error details).
	"""
	pass
