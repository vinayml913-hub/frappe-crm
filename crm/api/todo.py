import frappe
from frappe import _

from crm.fcrm.doctype.crm_notification.crm_notification import notify_user


def after_insert(doc, method):
	if doc.reference_type in ["CRM Lead", "CRM Deal"] and doc.reference_name and doc.allocated_to:
		fieldname = "lead_owner" if doc.reference_type == "CRM Lead" else "deal_owner"
		owner = frappe.db.get_value(doc.reference_type, doc.reference_name, fieldname)
		if not owner:
			frappe.db.set_value(
				doc.reference_type, doc.reference_name, fieldname, doc.allocated_to, update_modified=False
			)

	if doc.reference_type in ["CRM Lead", "CRM Deal", "CRM Task"] and doc.reference_name and doc.allocated_to:
		notify_assigned_user(doc)


def on_update(doc, method):
	if (
		doc.has_value_changed("status")
		and doc.status == "Cancelled"
		and doc.reference_type in ["CRM Lead", "CRM Deal", "CRM Task"]
		and doc.reference_name
		and doc.allocated_to
	):
		notify_assigned_user(doc, is_cancelled=True)


def notify_assigned_user(doc, is_cancelled=False):
	_doc = frappe.get_doc(doc.reference_type, doc.reference_name)
	owner = frappe.get_cached_value("User", frappe.session.user, "full_name")
	notification_text = get_notification_text(owner, doc, _doc, is_cancelled)

	message = (
		_("Your assignment on {0} {1} has been removed by {2}").format(
			doc.reference_type, doc.reference_name, owner
		)
		if is_cancelled
		else _("{0} assigned a {1} {2} to you").format(owner, doc.reference_type, doc.reference_name)
	)

	redirect_to_doctype, redirect_to_name = get_redirect_to_doc(doc)

	# 1. In-app bell notification (existing behaviour)
	notify_user(
		{
			"owner": frappe.session.user,
			"assigned_to": doc.allocated_to,
			"notification_type": "Assignment",
			"message": message,
			"notification_text": notification_text,
			"reference_doctype": doc.reference_type,
			"reference_docname": doc.reference_name,
			"redirect_to_doctype": redirect_to_doctype,
			"redirect_to_docname": redirect_to_name,
		}
	)

	# 2. Email notification (new) — only for new assignments, not on unassign
	if not is_cancelled:
		send_assignment_email(doc, owner, _doc)


def send_assignment_email(doc, assigner_full_name, reference_doc):
	"""Send an email to the assigned user when a Lead/Deal/Task is assigned to them."""
	try:
		assigned_to_email = doc.allocated_to
		if not assigned_to_email or assigned_to_email == frappe.session.user:
			return

		# Respect the user's own email-notification preference if they've turned it off
		if frappe.db.get_value("User", assigned_to_email, "enabled") == 0:
			return

		doctype_label = doc.reference_type.replace("CRM ", "")
		record_title = get_record_title(doc.reference_type, reference_doc)

		subject = _("{0} assigned you a {1}: {2}").format(
			assigner_full_name, doctype_label, record_title
		)

		crm_link = get_crm_link(doc)

		message = f"""
			<p>{_("Hi")},</p>
			<p>{_("{0} has assigned you a {1}").format(
				f"<b>{assigner_full_name}</b>", f"<b>{doctype_label}</b>"
			)}: <b>{record_title}</b></p>
			<p><a href="{crm_link}">{_("Click here to view it")}</a></p>
		"""

		frappe.sendmail(
			recipients=[assigned_to_email],
			subject=subject,
			message=message,
			reference_doctype=doc.reference_type,
			reference_name=doc.reference_name,
			now=True,
		)
	except Exception:
		# Never let an email failure block the assignment itself
		frappe.log_error(
			title="CRM Assignment Email Failed",
			message=frappe.get_traceback(),
		)


def get_record_title(reference_type, reference_doc):
	if reference_type == "CRM Lead":
		return reference_doc.lead_name or reference_doc.name
	if reference_type == "CRM Deal":
		return reference_doc.organization or reference_doc.lead_name or reference_doc.name
	if reference_type == "CRM Task":
		return reference_doc.title or reference_doc.name
	return reference_doc.name


def get_crm_link(doc):
	base_url = frappe.utils.get_url()
	redirect_to_doctype, redirect_to_name = get_redirect_to_doc(doc)
	if redirect_to_doctype == "CRM Deal":
		return f"{base_url}/crm/deals/{redirect_to_name}"
	if redirect_to_doctype == "CRM Lead":
		return f"{base_url}/crm/leads/{redirect_to_name}"
	return base_url + "/crm"


def get_notification_text(owner, doc, reference_doc, is_cancelled=False):
	name = doc.reference_name
	doctype = doc.reference_type

	if doctype.startswith("CRM "):
		doctype = doctype[4:].lower()

	if doctype in ["lead", "deal"]:
		name = (
			reference_doc.lead_name or name
			if doctype == "lead"
			else reference_doc.organization or reference_doc.lead_name or name
		)

		if is_cancelled:
			return f"""
                <div class="mb-2 leading-5 text-ink-gray-5">
                    <span>{ _('Your assignment on {0} {1} has been removed by {2}').format(
                        doctype,
                        f'<span class="font-medium text-ink-gray-9">{ name }</span>',
                        f'<span class="font-medium text-ink-gray-9">{ owner }</span>'
                    ) }</span>
                </div>
            """

		return f"""
            <div class="mb-2 leading-5 text-ink-gray-5">
                <span class="font-medium text-ink-gray-9">{ owner }</span>
                <span>{ _('assigned a {0} {1} to you').format(
                    doctype,
                    f'<span class="font-medium text-ink-gray-9">{ name }</span>'
                ) }</span>
            </div>
        """

	if doctype == "task":
		if is_cancelled:
			return f"""
                <div class="mb-2 leading-5 text-ink-gray-5">
                    <span>{ _('Your assignment on task {0} has been removed by {1}').format(
                        f'<span class="font-medium text-ink-gray-9">{ reference_doc.title }</span>',
                        f'<span class="font-medium text-ink-gray-9">{ owner }</span>'
                    ) }</span>
                </div>
            """
		return f"""
            <div class="mb-2 leading-5 text-ink-gray-5">
                <span class="font-medium text-ink-gray-9">{ owner }</span>
                <span>{ _('assigned a new task {0} to you').format(
                    f'<span class="font-medium text-ink-gray-9">{ reference_doc.title }</span>'
                ) }</span>
            </div>
        """


def get_redirect_to_doc(doc):
	if doc.reference_type == "CRM Task":
		reference_doc = frappe.get_doc(doc.reference_type, doc.reference_name)
		return reference_doc.reference_doctype, reference_doc.reference_docname

	return doc.reference_type, doc.reference_name
