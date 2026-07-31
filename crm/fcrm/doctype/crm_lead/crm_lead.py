# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.desk.form.assign_to import add as assign
from frappe.model.document import Document
from frappe.utils import has_gravatar, validate_email_address

from crm.fcrm.doctype.crm_service_level_agreement.utils import get_sla
from crm.fcrm.doctype.crm_status_change_log.crm_status_change_log import (
	add_status_change_log,
)
from crm.fcrm.doctype.utils import add_or_remove_lost_reason_section_in_sidepanel
from crm.utils.auto_create_links import auto_create_missing_links
from crm.utils.permissions import owner_only_has_permission, owner_only_query_conditions

# Record-level access to CRM Lead is strict "creator only", same rule as
# CRM Organization/Contact - see crm.utils.permissions. Only System
# Manager/Administrator bypass this. (Unlike CRM Deal, lead_owner/
# assign_to do NOT grant access here - confirmed with the business.)


def has_permission(doc, ptype=None, user=None):
	"""A CRM Lead is visible only to the user who created it, or to a
	System Manager/Administrator."""
	return owner_only_has_permission(doc, ptype=ptype, user=user)


def get_permission_query_conditions(user=None):
	"""List/kanban/report view counterpart to has_permission() above."""
	return owner_only_query_conditions("CRM Lead", user=user)


class CRMLead(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from crm.fcrm.doctype.crm_products.crm_products import CRMProducts
		from crm.fcrm.doctype.crm_rolling_response_time.crm_rolling_response_time import (
			CRMRollingResponseTime,
		)
		from crm.fcrm.doctype.crm_status_change_log.crm_status_change_log import CRMStatusChangeLog

		annual_revenue: DF.Currency
		communication_status: DF.Link | None
		converted: DF.Check
		email: DF.Data | None
		facebook_form_id: DF.Data | None
		facebook_lead_id: DF.Data | None
		first_name: DF.Data
		first_responded_on: DF.Datetime | None
		first_response_time: DF.Duration | None
		gender: DF.Link | None
		image: DF.AttachImage | None
		industry: DF.Link | None
		job_title: DF.Data | None
		last_name: DF.Data | None
		last_responded_on: DF.Datetime | None
		last_response_time: DF.Duration | None
		lead_name: DF.Data | None
		lead_owner: DF.Link | None
		lost_notes: DF.Text | None
		lost_reason: DF.Link | None
		middle_name: DF.Data | None
		mobile_no: DF.Data | None
		naming_series: DF.Literal["CRM-LEAD-.YYYY.-"]
		net_total: DF.Currency
		no_of_employees: DF.Literal["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
		organization: DF.Data | None
		phone: DF.Data | None
		products: DF.Table[CRMProducts]
		response_by: DF.Datetime | None
		rolling_responses: DF.Table[CRMRollingResponseTime]
		salutation: DF.Link | None
		sla: DF.Link | None
		sla_creation: DF.Datetime | None
		sla_status: DF.Literal["", "First Response Due", "Rolling Response Due", "Failed", "Fulfilled"]
		source: DF.Link | None
		status: DF.Link
		status_change_log: DF.Table[CRMStatusChangeLog]
		territory: DF.Link | None
		total: DF.Currency
		website: DF.Data | None
	# end: auto-generated types

	def before_validate(self):
		self.set_sla()
		# Lets Data Import/manual entry use any Territory or Lead Source
		# name freely - auto-creates the master record the first time
		# it's seen, instead of blocking with "Value does not exist".
		auto_create_missing_links(self, ["territory", "source"])

	def validate(self):
		self.validate_status()
		self.set_full_name()
		self.set_lead_name()
		self.set_title()
		self.validate_email()
		self.validate_lost_reason()
		if not self.is_new() and self.has_value_changed("lead_owner") and self.lead_owner:
			self.share_with_agent(self.lead_owner)
			self.assign_agent(self.lead_owner)
		if self.has_value_changed("status"):
			add_status_change_log(self)
		# Once this Lead already has its own Organization/Contact (created on
		# first insert - see after_insert), later edits to the org/POC fields
		# on the Lead should push forward into those SAME records rather than
		# spawning new ones. Only runs after the initial creation, and only
		# for fields that were actually touched.
		if not self.is_new():
			self.sync_linked_organization()
			self.sync_linked_contact()

	def after_insert(self):
		if self.lead_owner:
			if self.lead_owner != frappe.session.user:
				self.share_with_agent(self.lead_owner)
			self.assign_agent(self.lead_owner)
		# Every new Lead gets its OWN fresh Organization and Contact record in
		# the backend "master" tables - even if a same-named Organization or
		# same-email/phone Contact already exists elsewhere. This is
		# deliberate (confirmed with the business): no dedup, always create.
		self.always_create_organization()
		self.always_create_contact()

	def before_save(self):
		self.apply_sla()

	def validate_status(self):
		if self.is_new() and not self.status:
			if frappe.db.exists("CRM Lead Status", "New"):
				self.status = "New"
			else:
				self.status = frappe.get_all("CRM Lead Status", {"type": "Open"}, pluck="name")[0]

	def set_full_name(self):
		if self.first_name:
			self.lead_name = " ".join(
				name
				for name in [
					self.salutation,
					self.first_name,
					self.middle_name,
					self.last_name,
				]
				if name
			)

	def set_lead_name(self):
		if not self.lead_name:
			# Check for leads being created through data import
			if not self.organization and not self.email and not self.flags.ignore_mandatory:
				frappe.throw(_("A Lead requires either a person's name or an organization's name"))
			elif self.organization:
				self.lead_name = self.organization
			elif self.email:
				self.lead_name = self.email.split("@")[0]
			else:
				self.lead_name = "Unnamed Lead"

	def set_title(self):
		self.title = self.organization or self.lead_name

	def validate_email(self):
		if self.email:
			if not self.flags.ignore_email_validation:
				validate_email_address(self.email, throw=True)

			if self.email == self.lead_owner:
				frappe.throw(_("Lead Owner cannot be same as the Lead Email Address"))

			if self.is_new() or not self.image:
				self.image = has_gravatar(self.email)

	def validate_lost_reason(self):
		"""
		Validate the lost reason if the status is set to "Lost".
		"""
		if self.status and frappe.get_cached_value("CRM Lead Status", self.status, "type") == "Lost":
			if not self.lost_reason:
				frappe.throw(_("Please specify a reason for losing the lead."), frappe.ValidationError)
			elif self.lost_reason == "Other" and not self.lost_notes:
				frappe.throw(_("Please specify the reason for losing the lead."), frappe.ValidationError)
		if self.has_value_changed("status"):
			add_or_remove_lost_reason_section_in_sidepanel(self)

	def assign_agent(self, agent):
		if not agent:
			return

		assignees = self.get_assigned_users()
		if assignees:
			for assignee in assignees:
				if agent == assignee:
					# the agent is already set as an assignee
					return

		try:
			assign({"assign_to": [agent], "doctype": "CRM Lead", "name": self.name}, ignore_permissions=True)
		except TypeError:
			# Newer Frappe versions don't accept ignore_permissions on assign()
			assign({"assign_to": [agent], "doctype": "CRM Lead", "name": self.name})

	def share_with_agent(self, agent):
		if not agent:
			return

		docshares = frappe.get_all(
			"DocShare",
			filters={"share_name": self.name, "share_doctype": self.doctype},
			fields=["name", "user"],
		)

		shared_with = [d.user for d in docshares] + [agent]

		for user in shared_with:
			if user == agent and not frappe.db.exists(
				"DocShare",
				{"user": agent, "share_name": self.name, "share_doctype": self.doctype},
			):
				frappe.share.add_docshare(
					self.doctype,
					self.name,
					agent,
					write=1,
					flags={"ignore_share_permission": True},
				)
			elif user != agent:
				frappe.share.remove(
					self.doctype,
					self.name,
					user,
					flags={"ignore_share_permission": True, "ignore_permissions": True},
				)

	def always_create_organization(self):
		"""Create a brand-new CRM Organization for this Lead on first insert -
		no dedup by name, always a fresh record (per business decision).
		Links it back via linked_organization so later edits can sync
		forward, and so conversion can reuse it instead of creating a
		third copy - see create_organization()."""
		if not self.organization:
			return

		organization = frappe.new_doc("CRM Organization")
		organization.update(
			{
				"organization_name": self.organization,
				"website": self.website,
				"territory": self.territory,
				"industry": self.industry,
				"annual_revenue": self.annual_revenue,
			}
		)
		organization.insert(ignore_permissions=True)
		self.db_set("linked_organization", organization.name, update_modified=False)

	def always_create_contact(self):
		"""Create a brand-new Contact for this Lead's POC on first insert -
		no dedup by email/phone, always a fresh record (per business
		decision). Links it back via linked_contact so later edits can
		sync forward, and so conversion can reuse it - see create_contact()."""
		if not (self.first_name or self.last_name or self.email or self.mobile_no):
			return

		contact = frappe.new_doc("Contact")
		contact.update(
			{
				"first_name": self.first_name or self.lead_name or "Unnamed",
				"last_name": self.last_name,
				"salutation": self.salutation,
				"gender": self.gender,
				"designation": self.job_title,
				"company_name": self.organization,
				"image": self.image or "",
			}
		)
		if self.email:
			contact.append("email_ids", {"email_id": self.email, "is_primary": 1})
		if self.phone:
			contact.append("phone_nos", {"phone": self.phone, "is_primary_phone": 1})
		if self.mobile_no:
			contact.append("phone_nos", {"phone": self.mobile_no, "is_primary_mobile_no": 1})
		contact.insert(ignore_permissions=True)
		self.db_set("linked_contact", contact.name, update_modified=False)

	def sync_linked_organization(self):
		"""If org-related fields were edited on an existing Lead that already
		has its own linked Organization, push those edits into that same
		record instead of creating another one."""
		if not self.linked_organization:
			return
		org_fields = ("organization", "website", "territory", "industry", "annual_revenue")
		if not any(self.has_value_changed(f) for f in org_fields):
			return
		if not frappe.db.exists("CRM Organization", self.linked_organization):
			return
		frappe.db.set_value(
			"CRM Organization",
			self.linked_organization,
			{
				"organization_name": self.organization,
				"website": self.website,
				"territory": self.territory,
				"industry": self.industry,
				"annual_revenue": self.annual_revenue,
			},
		)

	def sync_linked_contact(self):
		"""If POC fields were edited on an existing Lead that already has its
		own linked Contact, push those edits into that same Contact record
		instead of creating another one."""
		if not self.linked_contact:
			return
		poc_fields = ("first_name", "last_name", "salutation", "gender", "job_title", "email", "phone", "mobile_no")
		if not any(self.has_value_changed(f) for f in poc_fields):
			return
		contact = frappe.db.exists("Contact", self.linked_contact)
		if not contact:
			return
		contact = frappe.get_doc("Contact", self.linked_contact)
		contact.first_name = self.first_name or contact.first_name
		contact.last_name = self.last_name
		contact.salutation = self.salutation
		contact.gender = self.gender
		contact.designation = self.job_title
		contact.company_name = self.organization
		if self.email and self.has_value_changed("email"):
			contact.set("email_ids", [])
			contact.append("email_ids", {"email_id": self.email, "is_primary": 1})
		if self.mobile_no and self.has_value_changed("mobile_no"):
			contact.set(
				"phone_nos",
				[p for p in contact.phone_nos if not p.is_primary_mobile_no],
			)
			contact.append("phone_nos", {"phone": self.mobile_no, "is_primary_mobile_no": 1})
		contact.save(ignore_permissions=True)

	def create_contact(self, existing_contact=None, throw=True):
		if not self.lead_name:
			self.set_full_name()
			self.set_lead_name()

		# At conversion time, prefer the Contact that was already created for
		# this Lead when it was first inserted (see always_create_contact),
		# rather than spawning yet another one for the same Lead.
		existing_contact = existing_contact or self.linked_contact or self.contact_exists(throw)
		if existing_contact:
			self.update_lead_contact(existing_contact)
			return existing_contact

		contact = frappe.new_doc("Contact")
		contact.update(
			{
				"first_name": self.first_name or self.lead_name,
				"last_name": self.last_name,
				"salutation": self.salutation,
				"gender": self.gender,
				"designation": self.job_title,
				"company_name": self.organization,
				"image": self.image or "",
			}
		)

		if self.email:
			contact.append("email_ids", {"email_id": self.email, "is_primary": 1})

		if self.phone:
			contact.append("phone_nos", {"phone": self.phone, "is_primary_phone": 1})

		if self.mobile_no:
			contact.append("phone_nos", {"phone": self.mobile_no, "is_primary_mobile_no": 1})

		contact.insert(ignore_permissions=True)
		contact.reload()  # load changes by hooks on contact

		return contact.name

	def create_organization(self, existing_organization=None):
		if not self.organization and not existing_organization:
			return

		# At conversion time, prefer the Organization already created for this
		# Lead on insert (see always_create_organization) over matching by
		# name or creating a fresh one - avoids a third duplicate record.
		existing_organization = (
			existing_organization
			or self.linked_organization
			or frappe.db.exists("CRM Organization", {"organization_name": self.organization})
		)
		if existing_organization:
			self.db_set("organization", existing_organization)
			return existing_organization

		organization = frappe.new_doc("CRM Organization")
		organization.update(
			{
				"organization_name": self.organization,
				"website": self.website,
				"territory": self.territory,
				"industry": self.industry,
				"annual_revenue": self.annual_revenue,
			}
		)
		organization.insert(ignore_permissions=True)
		return organization.name

	def update_lead_contact(self, contact):
		contact = frappe.get_cached_doc("Contact", contact)
		frappe.db.set_value(
			"CRM Lead",
			self.name,
			{
				"salutation": contact.salutation,
				"first_name": contact.first_name,
				"last_name": contact.last_name,
				"email": contact.email_id,
				"mobile_no": contact.mobile_no,
			},
		)

	def contact_exists(self, throw=True):
		email_exist = frappe.db.exists("Contact Email", {"email_id": self.email})
		phone_exist = frappe.db.exists("Contact Phone", {"phone": self.phone})
		mobile_exist = frappe.db.exists("Contact Phone", {"phone": self.mobile_no})

		doctype = "Contact Email" if email_exist else "Contact Phone"
		name = email_exist or phone_exist or mobile_exist

		if name:
			text = "Email" if email_exist else "Phone" if phone_exist else "Mobile No"
			data = self.email if email_exist else self.phone if phone_exist else self.mobile_no

			value = "{0}: {1}".format(text, data)

			contact = frappe.db.get_value(doctype, name, "parent")

			if throw:
				frappe.throw(
					_("Contact already exists with {0}").format(value),
					title=_("Contact Already Exists"),
				)
			return contact

		return False

	def create_deal(self, contact, organization, deal=None):
		new_deal = frappe.new_doc("CRM Deal")

		lead_deal_map = {
			"lead_owner": "deal_owner",
		}

		restricted_fieldtypes = [
			"Tab Break",
			"Section Break",
			"Column Break",
			"HTML",
			"Button",
			"Attach",
		]
		restricted_map_fields = [
			"name",
			"naming_series",
			"creation",
			"owner",
			"modified",
			"modified_by",
			"idx",
			"docstatus",
			"status",
			"email",
			"mobile_no",
			"phone",
			"sla",
			"sla_status",
			"response_by",
			"first_response_time",
			"first_responded_on",
			"communication_status",
			"sla_creation",
			"status_change_log",
		]

		for field in self.meta.fields:
			if field.fieldtype in restricted_fieldtypes:
				continue
			if field.fieldname in restricted_map_fields:
				continue

			fieldname = field.fieldname
			if field.fieldname in lead_deal_map:
				fieldname = lead_deal_map[field.fieldname]

			if hasattr(new_deal, fieldname):
				if fieldname == "organization":
					new_deal.update({fieldname: organization})
				else:
					new_deal.update({fieldname: self.get(field.fieldname)})

		new_deal.update(
			{
				"lead": self.name,
				"contacts": [{"contact": contact}],
			}
		)

		if self.first_responded_on:
			new_deal.update(
				{
					"sla_creation": self.sla_creation,
					"response_by": self.response_by,
					"sla_status": self.sla_status,
					"communication_status": self.communication_status,
					"first_response_time": self.first_response_time,
					"first_responded_on": self.first_responded_on,
				}
			)

		if deal:
			new_deal.update(deal)

		new_deal.insert(ignore_permissions=True)

		for user in self.get_assigned_users():
			if user and user != new_deal.deal_owner:
				new_deal.assign_agent(user)

		return new_deal.name

	def set_sla(self):
		"""
		Find an SLA to apply to the lead.
		"""
		if self.sla:
			return

		sla = get_sla(self)
		if not sla:
			self.first_responded_on = None
			self.first_response_time = None
			return
		self.sla = sla.name

	def apply_sla(self):
		"""
		Apply SLA if set.
		"""
		if not self.sla:
			return
		sla = frappe.get_last_doc("CRM Service Level Agreement", {"name": self.sla})
		if sla:
			sla.apply(self)

	def convert_to_deal(self, deal=None):
		return convert_to_deal(lead=self.name, doc=self, deal=deal)

	@staticmethod
	def get_non_filterable_fields():
		return ["converted"]

	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Name",
				"type": "Data",
				"key": "lead_name",
				"width": "12rem",
			},
			{
				"label": "Organization",
				"type": "Link",
				"key": "organization",
				"options": "CRM Organization",
				"width": "10rem",
			},
			{
				"label": "Status",
				"type": "Link",
				"options": "CRM Lead Status",
				"key": "status",
				"width": "8rem",
			},
			{
				"label": "Email",
				"type": "Data",
				"key": "email",
				"width": "12rem",
			},
			{
				"label": "Mobile No.",
				"type": "Data",
				"key": "mobile_no",
				"width": "11rem",
			},
			{
				"label": "Assigned To",
				"type": "Text",
				"key": "_assign",
				"width": "10rem",
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
			"lead_name",
			"organization",
			"status",
			"email",
			"mobile_no",
			"lead_owner",
			"first_name",
			"sla_status",
			"response_by",
			"first_response_time",
			"first_responded_on",
			"modified",
			"_assign",
			"image",
		]
		return {"columns": columns, "rows": rows}

	@staticmethod
	def default_kanban_settings():
		return {
			"column_field": "status",
			"title_field": "lead_name",
			"kanban_fields": '["organization", "email", "mobile_no", "_assign", "modified"]',
		}


@frappe.whitelist()
def convert_to_deal(
	lead: str,
	doc: Document | None = None,
	deal: str | dict | None = None,
	existing_contact: str | None = None,
	existing_organization: str | None = None,
):
	if not (doc and doc.flags.get("ignore_permissions")) and not frappe.has_permission(
		"CRM Lead", "write", lead
	):
		frappe.throw(_("Not allowed to convert Lead to Deal"), frappe.PermissionError)

	lead = frappe.get_cached_doc("CRM Lead", lead)
	if frappe.db.exists("CRM Lead Status", "Qualified"):
		lead.db_set("status", "Qualified")
	lead.db_set("converted", 1)
	if lead.sla and frappe.db.exists("CRM Communication Status", "Replied"):
		lead.db_set("communication_status", "Replied")
	contact = lead.create_contact(existing_contact, False)
	organization = lead.create_organization(existing_organization)
	_deal = lead.create_deal(contact, organization, deal)
	return _deal


@frappe.whitelist()
def backfill_organization_and_contact_for_existing_leads(dry_run: bool = True, limit: int = 0):
	"""One-time backfill for Leads created BEFORE the always_create_organization/
	always_create_contact feature existed. Runs the same "always create, no
	dedup" logic on every Lead that doesn't yet have a linked_organization or
	linked_contact.

	Call with dry_run=True first (default) to see how many leads would be
	affected before actually creating anything. Then call again with
	dry_run=False to run it for real.

	Trigger via:
	  /api/method/crm.fcrm.doctype.crm_lead.crm_lead.backfill_organization_and_contact_for_existing_leads?dry_run=1
	  /api/method/crm.fcrm.doctype.crm_lead.crm_lead.backfill_organization_and_contact_for_existing_leads?dry_run=0&limit=500
	"""
	if not frappe.has_permission("CRM Lead", "write"):
		frappe.throw(_("Not allowed to run this"), frappe.PermissionError)

	dry_run = frappe.parse_json(dry_run) if isinstance(dry_run, str) else dry_run
	limit = int(limit) if limit else 0

	# OR, not AND - a lead that already has ONE of the two links (e.g. from a
	# partial/failed previous run) should still be retried for the other.
	or_filters = [
		["linked_organization", "in", ["", None]],
		["linked_contact", "in", ["", None]],
	]
	lead_names = frappe.get_all(
		"CRM Lead",
		or_filters=or_filters,
		pluck="name",
		limit_page_length=limit if limit else 1_000_000,
		order_by="creation asc",
	)

	if dry_run:
		return {
			"dry_run": True,
			"leads_that_would_be_processed": len(lead_names),
			"note": "Call again with dry_run=0 (and optionally limit=N to batch it) to actually create records.",
		}

	created_org, created_contact, skipped_no_org_data, skipped_no_contact_data, failed = 0, 0, 0, 0, []
	for lead_name in lead_names:
		try:
			lead = frappe.get_doc("CRM Lead", lead_name)
			if not lead.linked_organization:
				lead.always_create_organization()
				if lead.linked_organization:
					created_org += 1
				else:
					skipped_no_org_data += 1  # lead.organization was blank
			if not lead.linked_contact:
				lead.always_create_contact()
				if lead.linked_contact:
					created_contact += 1
				else:
					skipped_no_contact_data += 1  # no first/last name, email, or mobile
			frappe.db.commit()
		except Exception as e:
			frappe.db.rollback()
			failed.append({"lead": lead_name, "error": str(e)})
			frappe.log_error(title=f"Backfill failed for Lead {lead_name}")

	return {
		"dry_run": False,
		"total_leads_matched": len(lead_names),
		"organizations_created": created_org,
		"contacts_created": created_contact,
		"skipped_leads_with_no_organization_text": skipped_no_org_data,
		"skipped_leads_with_no_poc_fields": skipped_no_contact_data,
		"failed": failed,
	}
