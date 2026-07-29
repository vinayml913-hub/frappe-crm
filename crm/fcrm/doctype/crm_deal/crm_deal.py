# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.desk.form.assign_to import add as assign
from frappe.model.document import Document

from crm.api.exchange_rate import get_exchange_rate
from crm.fcrm.doctype.crm_service_level_agreement.utils import get_sla
from crm.fcrm.doctype.crm_status_change_log.crm_status_change_log import add_status_change_log
from crm.fcrm.doctype.utils import add_or_remove_lost_reason_section_in_sidepanel
from crm.utils.auto_create_links import auto_create_missing_links

# Users who can always see every deal, regardless of whether they're
# personally tied to it.
DEAL_ADMIN_ROLES = ("System Manager",)

# Fields on CRM Deal that name a specific person tied to that deal. Anyone
# named in one of these fields (on that particular deal) can see it, in
# addition to the deal's creator and whoever it's assigned to.
DEAL_PERSON_FIELDS = ("deal_owner", "sales_manager", "account_manager", "training_engagement_manager")


def _is_deal_admin(user):
	return user == "Administrator" or bool(set(frappe.get_roles(user)) & set(DEAL_ADMIN_ROLES))


def has_permission(doc, ptype=None, user=None):
	"""Restrict direct access to a single CRM Deal to: the deal's creator,
	its deal_owner/sales_manager/account_manager(Solution Manager)/
	training_engagement_manager, anyone it's assigned to, anyone it's been
	explicitly shared with, or a System Manager/Administrator."""
	user = user or frappe.session.user
	if _is_deal_admin(user):
		return True

	if doc.get("owner") == user:
		return True

	if any(doc.get(fieldname) == user for fieldname in DEAL_PERSON_FIELDS):
		return True

	assigned = doc.get("_assign")
	if assigned:
		try:
			assigned = json.loads(assigned) if isinstance(assigned, str) else assigned
		except (TypeError, ValueError):
			assigned = []
		if user in (assigned or []):
			return True

	if user in frappe.share.get_users(doc.doctype, doc.name):
		return True

	return False


def get_permission_query_conditions(user=None):
	"""Restrict the CRM Deal list/kanban/report views the same way as
	has_permission() above, so users only see deals they're tied to."""
	user = user or frappe.session.user
	if _is_deal_admin(user):
		return ""

	user_e = frappe.db.escape(user)
	assign_match_e = frappe.db.escape(f"%{user}%")
	person_conditions = " OR ".join(
		f"`tabCRM Deal`.`{fieldname}` = {user_e}" for fieldname in DEAL_PERSON_FIELDS
	)

	return f"""(
		`tabCRM Deal`.`owner` = {user_e}
		OR {person_conditions}
		OR `tabCRM Deal`.`_assign` LIKE {assign_match_e}
		OR `tabCRM Deal`.`name` IN (
			SELECT share_name FROM `tabDocShare`
			WHERE share_doctype = 'CRM Deal' AND user = {user_e}
		)
	)"""


class CRMDeal(Document):
	# begin: auto-generated types
	from typing import TYPE_CHECKING
	if TYPE_CHECKING:
		from frappe.types import DF
		from crm.fcrm.doctype.crm_contacts.crm_contacts import CRMContacts
		from crm.fcrm.doctype.crm_products.crm_products import CRMProducts
		from crm.fcrm.doctype.crm_rolling_response_time.crm_rolling_response_time import CRMRollingResponseTime
		from crm.fcrm.doctype.crm_status_change_log.crm_status_change_log import CRMStatusChangeLog

		annual_revenue: DF.Currency
		closed_date: DF.Date | None
		communication_status: DF.Link | None
		contact: DF.Link | None
		contacts: DF.Table[CRMContacts]
		currency: DF.Link | None
		deal_owner: DF.Link | None
		deal_value: DF.Currency
		email: DF.Data | None
		exchange_rate: DF.Float
		expected_closure_date: DF.Date | None
		expected_deal_value: DF.Currency
		first_name: DF.Data | None
		first_responded_on: DF.Datetime | None
		first_response_time: DF.Duration | None
		gender: DF.Link | None
		industry: DF.Link | None
		job_title: DF.Data | None
		last_name: DF.Data | None
		last_responded_on: DF.Datetime | None
		last_response_time: DF.Duration | None
		lead: DF.Link | None
		lead_name: DF.Data | None
		lost_notes: DF.Text | None
		lost_reason: DF.Link | None
		mobile_no: DF.Data | None
		naming_series: DF.Literal["CRM-DEAL-.YYYY.-"]
		net_total: DF.Currency
		next_step: DF.Data | None
		no_of_employees: DF.Literal["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
		organization: DF.Link | None
		organization_name: DF.Data | None
		phone: DF.Data | None
		probability: DF.Percent
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
		# PBS Deal Details
		deal_name: DF.Data | None
		account: DF.Link | None
		expected_close_date: DF.Date | None
		stage: DF.Data | None
		probability_pct: DF.Percent
		# PBS Costing & Trainer
		trainer_commercial: DF.Currency
		costing_type: DF.Data | None
		no_of_days: DF.Int
		no_of_hours: DF.Float
		trainer_cost: DF.Currency
		lab_expense: DF.Currency
		total_expense: DF.Currency
		# PBS Financial Summary
		margin_pct: DF.Int
		gst_percentage: DF.Int
		gross_profit: DF.Currency
		gst_amount: DF.Currency
		base_amount: DF.Currency
		final_amount: DF.Currency
		gross_profit_pct: DF.Percent
		# PBS Other
		lead_source: DF.Link | None
		lab_required: DF.Check
		training_required: DF.Check
		sales_manager: DF.Link | None
		account_manager: DF.Link | None
		training_engagement_manager: DF.Link | None
		accounting_notes: DF.TextEditor | None
		te_notes: DF.TextEditor | None
		# PBS Project Info
		technology: DF.Data | None
		delivery_type: DF.Data | None
		duration: DF.Data | None
		start_date: DF.Date | None
		end_date: DF.Date | None
		delivery_date: DF.Date | None
		# PBS Trainer Details
		trainer: DF.Link | None
		trainer_status: DF.Data | None
		trainer_notes: DF.TextEditor | None
		costing_remarks: DF.TextEditor | None
	# end: auto-generated types

	def before_validate(self):
		self.set_sla()
		# Lets Data Import/manual entry use any Territory or Lead Source
		# name freely - auto-creates the master record the first time
		# it's seen, instead of blocking with "Value does not exist".
		auto_create_missing_links(self, ["territory", "source", "lead_source"])

	def validate(self):
		self.validate_status()
		self.set_primary_contact()
		self.set_primary_email_mobile_no()
		if not self.is_new() and self.has_value_changed("deal_owner") and self.deal_owner:
			self.share_with_agent(self.deal_owner)
			self.assign_agent(self.deal_owner)
		# Team fields (Sales Manager / Solution Manager / Training Engagement
		# Co-ordinator) only ever set a plain value on the record - unlike
		# deal_owner, they never actually notified anyone. Give them the
		# same assign (-> ToDo -> notification) behaviour deal_owner
		# already gets, whenever one of these fields is set/changed.
		# NOTE: deliberately NOT calling share_with_agent() here - that
		# method is written to be exclusive to a single agent (it revokes
		# DocShare from anyone else), so calling it for three different
		# people would keep clobbering each other's access. It's also
		# unnecessary: view access for these fields is already granted
		# independently via has_permission()'s DEAL_PERSON_FIELDS check.
		if not self.is_new():
			for fieldname in ("sales_manager", "account_manager", "training_engagement_manager"):
				if self.has_value_changed(fieldname) and self.get(fieldname):
					self.assign_agent(self.get(fieldname))
		if self.has_value_changed("status"):
			add_status_change_log(self)
			if frappe.db.get_value("CRM Deal Status", self.status, "type") == "Won":
				self.closed_date = frappe.utils.nowdate()
		self.validate_forecasting_fields()
		self.validate_lost_reason()
		self.update_exchange_rate()
		self.calculate_financials()

	def after_insert(self):
		if self.deal_owner:
			if self.deal_owner != frappe.session.user:
				self.share_with_agent(self.deal_owner)
			self.assign_agent(self.deal_owner)
		# Same Team-field notification fix as validate() above, for the
		# case where these fields are already filled in on first creation
		# (e.g. the "Team" section of the New Deal dialog) rather than
		# added later as an edit. No share_with_agent() here either - see
		# the comment in validate() for why.
		for fieldname in ("sales_manager", "account_manager", "training_engagement_manager"):
			value = self.get(fieldname)
			if value:
				self.assign_agent(value)

	def before_save(self):
		self.apply_sla()

	def calculate_financials(self):
		"""
		Complete PBS Financial Calculation:

		1. Trainer Cost = Trainer Commercial × Days/Hours
		2. Total Expense = Trainer Cost + Lab Expense
		3. GP = Total Expense × Margin% / 100
		4. Base Amount = Total Expense + GP
		5. GST Amount = Base Amount × GST% / 100
		6. Final Amount = Base Amount + GST Amount
		7. GP% = GP / Base Amount × 100
		"""
		trainer_commercial = float(self.trainer_commercial or 0)
		costing_type = self.costing_type or ""
		no_of_days = int(self.no_of_days or 0)
		no_of_hours = float(self.no_of_hours or 0)
		lab_expense = float(self.lab_expense or 0)
		gst_pct = float(self.gst_percentage or 18)

		# Default Margin % to 20 if left blank, so GP is never silently zero
		if not self.margin_pct:
			self.margin_pct = 20
		margin_pct = float(self.margin_pct or 0)

		# Step 1: Trainer Cost
		if costing_type == "Per Day":
			self.trainer_cost = trainer_commercial * no_of_days
		elif costing_type == "Per Hour":
			self.trainer_cost = trainer_commercial * no_of_hours
		else:
			self.trainer_cost = trainer_commercial

		trainer_cost = float(self.trainer_cost or 0)

		# Step 2: Total Expense
		self.total_expense = trainer_cost + lab_expense

		total_expense = float(self.total_expense or 0)

		if total_expense > 0 and margin_pct > 0:
			# Step 3: Gross Profit
			self.gross_profit = total_expense * margin_pct / 100

			# Step 4: Base Amount
			self.base_amount = total_expense + self.gross_profit

			# Step 5: GST Amount
			self.gst_amount = self.base_amount * gst_pct / 100

			# Step 6: Final Amount
			self.final_amount = self.base_amount + self.gst_amount

			# Step 7: GP%
			self.gross_profit_pct = (self.gross_profit / self.base_amount) * 100
		else:
			self.gross_profit = 0
			self.base_amount = total_expense
			self.gst_amount = total_expense * gst_pct / 100
			self.final_amount = total_expense + self.gst_amount
			self.gross_profit_pct = 0

	def validate_status(self):
		if self.is_new() and not self.status:
			if frappe.db.exists("CRM Deal Status", "Qualified"):
				self.status = "Qualified"
			else:
				self.status = frappe.get_all("CRM Deal Status", {"type": "Open"}, pluck="name")[0]

	def set_primary_contact(self, contact=None):
		if not self.contacts:
			return
		if not contact and len(self.contacts) == 1:
			self.contacts[0].is_primary = 1
		elif contact:
			for d in self.contacts:
				if d.contact == contact:
					d.is_primary = 1
				else:
					d.is_primary = 0

	def set_primary_email_mobile_no(self):
		if not self.contacts:
			self.email = ""
			self.mobile_no = ""
			self.phone = ""
			return
		if len([c for c in self.contacts if c.is_primary]) > 1:
			frappe.throw(_("Only one {0} can be set as primary.").format(frappe.bold("Contact")))
		primary_contact_exists = False
		for d in self.contacts:
			if d.is_primary == 1:
				primary_contact_exists = True
				self.email = d.email.strip() if d.email else ""
				self.mobile_no = d.mobile_no.strip() if d.mobile_no else ""
				self.phone = d.phone.strip() if d.phone else ""
				break
		if not primary_contact_exists:
			self.email = ""
			self.mobile_no = ""
			self.phone = ""

	def assign_agent(self, agent):
		if not agent:
			return
		assignees = self.get_assigned_users()
		if assignees:
			for assignee in assignees:
				if agent == assignee:
					return
		try:
			assign({"assign_to": [agent], "doctype": "CRM Deal", "name": self.name}, ignore_permissions=True)
		except TypeError:
			# Newer Frappe versions don't accept ignore_permissions on assign()
			assign({"assign_to": [agent], "doctype": "CRM Deal", "name": self.name})

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
					self.doctype, self.name, agent, write=1,
					flags={"ignore_share_permission": True},
				)
			elif user != agent:
				frappe.share.remove(
					self.doctype, self.name, user,
					flags={"ignore_share_permission": True, "ignore_permissions": True},
				)

	def set_sla(self):
		if self.sla:
			return
		sla = get_sla(self)
		if not sla:
			self.first_responded_on = None
			self.first_response_time = None
			return
		self.sla = sla.name

	def apply_sla(self):
		if not self.sla:
			return
		sla = frappe.get_last_doc("CRM Service Level Agreement", {"name": self.sla})
		if sla:
			sla.apply(self)

	def update_closed_date(self):
		if self.status == "Won" and not self.closed_date:
			self.closed_date = frappe.utils.nowdate()

	def update_default_probability(self):
		if not self.probability or self.probability == 0:
			self.probability = frappe.db.get_value("CRM Deal Status", self.status, "probability") or 0

	def update_expected_deal_value(self):
		if (
			frappe.db.get_single_value("FCRM Settings", "auto_update_expected_deal_value")
			and (self.net_total or self.total)
			and self.expected_deal_value
		):
			self.expected_deal_value = self.net_total or self.total

	def validate_forecasting_fields(self):
		self.update_closed_date()
		self.update_default_probability()
		self.update_expected_deal_value()
		if frappe.db.get_single_value("FCRM Settings", "enable_forecasting"):
			if not self.expected_deal_value or self.expected_deal_value == 0:
				frappe.throw(_("Expected deal value is required."), frappe.MandatoryError)
			if not self.expected_closure_date:
				frappe.throw(_("Expected closure date is required."), frappe.MandatoryError)

	def validate_lost_reason(self):
		if self.status and frappe.get_cached_value("CRM Deal Status", self.status, "type") == "Lost":
			if not self.lost_reason:
				frappe.throw(_("Please specify a reason for losing the deal."), frappe.ValidationError)
			elif self.lost_reason == "Other" and not self.lost_notes:
				frappe.throw(_("Please specify the reason for losing the deal."), frappe.ValidationError)
		if self.has_value_changed("status"):
			add_or_remove_lost_reason_section_in_sidepanel(self)

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
			{"label": "Organization", "type": "Link", "key": "organization", "options": "CRM Organization", "width": "11rem"},
			{"label": "Annual Revenue", "type": "Currency", "key": "annual_revenue", "align": "right", "width": "9rem"},
			{"label": "Status", "type": "Link", "options": "CRM Deal Status", "key": "status", "width": "10rem"},
			{"label": "Email", "type": "Data", "key": "email", "width": "12rem"},
			{"label": "Mobile No.", "type": "Data", "key": "mobile_no", "width": "11rem"},
			{"label": "Assigned To", "type": "Text", "key": "_assign", "width": "10rem"},
			{"label": "Last Modified", "type": "Datetime", "key": "modified", "width": "8rem"},
		]
		rows = [
			"name", "organization", "annual_revenue", "status", "email",
			"currency", "mobile_no", "deal_owner", "sla_status", "response_by",
			"first_response_time", "first_responded_on", "modified", "_assign",
		]
		return {"columns": columns, "rows": rows}

	@staticmethod
	def default_kanban_settings():
		return {
			"column_field": "status",
			"title_field": "organization",
			"kanban_fields": '["annual_revenue", "email", "mobile_no", "_assign", "modified"]',
		}


@frappe.whitelist()
def add_contact(deal: str, contact: str):
	if not frappe.has_permission("CRM Deal", "write", deal):
		frappe.throw(_("Not allowed to add contact to Deal"), frappe.PermissionError)
	deal = frappe.get_cached_doc("CRM Deal", deal)
	deal.append("contacts", {"contact": contact})
	deal.save()
	return True


@frappe.whitelist()
def remove_contact(deal: str, contact: str):
	if not frappe.has_permission("CRM Deal", "write", deal):
		frappe.throw(_("Not allowed to remove contact from Deal"), frappe.PermissionError)
	deal = frappe.get_cached_doc("CRM Deal", deal)
	deal.contacts = [d for d in deal.contacts if d.contact != contact]
	deal.save()
	return True


@frappe.whitelist()
def set_primary_contact(deal: str, contact: str):
	if not frappe.has_permission("CRM Deal", "write", deal):
		frappe.throw(_("Not allowed to set primary contact for Deal"), frappe.PermissionError)
	deal = frappe.get_cached_doc("CRM Deal", deal)
	deal.set_primary_contact(contact)
	deal.save()
	return True


def create_organization(doc):
	if not doc.get("organization_name"):
		return
	existing_organization = frappe.db.exists(
		"CRM Organization", {"organization_name": doc.get("organization_name")}
	)
	if existing_organization:
		return existing_organization
	organization = frappe.new_doc("CRM Organization")
	organization.update({
		"organization_name": doc.get("organization_name"),
		"website": doc.get("website"),
		"territory": doc.get("territory"),
		"industry": doc.get("industry"),
		"annual_revenue": doc.get("annual_revenue"),
	})
	organization.insert(ignore_permissions=True)
	return organization.name


def contact_exists(doc):
	email_exist = frappe.db.exists("Contact Email", {"email_id": doc.get("email")})
	mobile_exist = frappe.db.exists("Contact Phone", {"phone": doc.get("mobile_no")})
	doctype = "Contact Email" if email_exist else "Contact Phone"
	name = email_exist or mobile_exist
	if name:
		return frappe.db.get_value(doctype, name, "parent")
	return False


def create_contact(doc):
	existing_contact = contact_exists(doc)
	if existing_contact:
		return existing_contact
	contact = frappe.new_doc("Contact")
	contact.update({
		"first_name": doc.get("first_name"),
		"last_name": doc.get("last_name"),
		"salutation": doc.get("salutation"),
		"company_name": doc.get("organization") or doc.get("organization_name"),
		"gender": doc.get("gender"),
	})
	if doc.get("email"):
		contact.append("email_ids", {"email_id": doc.get("email"), "is_primary": 1})
	if doc.get("mobile_no"):
		contact.append("phone_nos", {"phone": doc.get("mobile_no"), "is_primary_mobile_no": 1})
	contact.insert(ignore_permissions=True)
	contact.reload()
	return contact.name


@frappe.whitelist()
def create_deal(doc: dict):
	deal = frappe.new_doc("CRM Deal")
	contact = doc.get("contact")
	if not contact and (
		doc.get("first_name") or doc.get("last_name") or doc.get("email") or doc.get("mobile_no")
	):
		contact = create_contact(doc)
	deal.update({
		"organization": doc.get("organization") or create_organization(doc),
		"contacts": [{"contact": contact, "is_primary": 1}] if contact else [],
	})
	doc.pop("organization", None)
	deal.update(doc)
	deal.insert(ignore_permissions=True)
	return deal.name
