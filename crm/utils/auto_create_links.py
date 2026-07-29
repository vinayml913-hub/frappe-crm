# Copyright (c) 2026, Pioneer Business Solutions and contributors
# For license information, please see license.txt

import frappe

# Maps a Link field's target doctype to its title/autoname field, so we
# know which field to set when auto-creating a missing record.
# Add more doctype: title-field pairs here if other Link fields need the
# same "accept any value from Excel, auto-create if missing" behaviour.
AUTO_CREATABLE_LINKS = {
	"CRM Territory": "territory_name",
	"CRM Lead Source": "source_name",
}


def get_or_create_link(doctype: str, value: str) -> str | None:
	"""
	If `value` already exists as a record name in `doctype`, return it
	unchanged. Otherwise create a minimal new record with just the
	title field set, and return that.

	This lets CSV/Excel imports use any Territory or Lead Source name
	freely - instead of the import being blocked with a "Value does
	not exist" warning and the field being left blank - by creating
	the missing master record on the fly the first time it's seen.

	Returns None if `value` is empty (nothing to do) or if `doctype`
	isn't registered in AUTO_CREATABLE_LINKS (safety: only ever
	auto-creates for doctypes explicitly opted in here).
	"""
	value = (value or "").strip()
	if not value:
		return None

	title_field = AUTO_CREATABLE_LINKS.get(doctype)
	if not title_field:
		return None

	if frappe.db.exists(doctype, value):
		return value

	new_doc = frappe.get_doc({"doctype": doctype, title_field: value})
	new_doc.insert(ignore_permissions=True)
	return new_doc.name


def auto_create_missing_links(doc, link_fields: list[str]):
	"""
	Call from a document's before_validate: for each fieldname in
	`link_fields`, if it holds a value that doesn't exist yet as a
	record in that field's target doctype, auto-create it (via
	get_or_create_link) instead of letting core Link validation throw.

	`link_fields` are plain Document field names (e.g. "territory",
	"source") - the target doctype is read from the field's own
	`options` (the Link field's `options` = the doctype it points to),
	so this stays correct even if a doctype's field options change.
	"""
	meta = doc.meta
	for fieldname in link_fields:
		field = meta.get_field(fieldname)
		if not field or field.fieldtype != "Link":
			continue
		target_doctype = field.options
		if target_doctype not in AUTO_CREATABLE_LINKS:
			continue

		value = doc.get(fieldname)
		if not value:
			continue

		resolved = get_or_create_link(target_doctype, value)
		if resolved:
			doc.set(fieldname, resolved)
