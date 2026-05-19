import frappe

def execute():
    quick_entry_layout = '[{"name": "person_section", "columns": [{"name": "column_5jrk", "fields": ["salutation", "email"]}, {"name": "column_5CPV", "fields": ["first_name", "mobile_no"]}, {"name": "column_gXOy", "fields": ["last_name", "gender"]}]}, {"name": "organization_section", "columns": [{"name": "column_GHfX", "fields": ["organization", "territory"]}, {"name": "column_hXjS", "fields": ["website", "annual_revenue"]}, {"name": "column_RDNA", "fields": ["no_of_employees", "industry"]}]}, {"name": "lead_section", "columns": [{"name": "column_EO1H", "fields": ["status"]}, {"name": "column_RWBe", "fields": ["lead_owner"]}]}, {"name": "description_section", "columns": [{"name": "column_DESC", "fields": ["description"]}]}]'

    side_panel_layout = '[{"label": "Details", "name": "details_section", "opened": true, "columns": [{"name": "column_kl92", "fields": ["organization", "website", "territory", "industry", "job_title", "source", "lead_owner"]}]}, {"label": "Person", "name": "person_section", "opened": true, "columns": [{"name": "column_XmW2", "fields": ["salutation", "first_name", "last_name", "email", "mobile_no"]}]}, {"label": "Description", "name": "description_section", "opened": true, "columns": [{"name": "column_DESC2", "fields": ["description"]}]}]'

    if frappe.db.exists("CRM Fields Layout", "CRM Lead-Quick Entry"):
        frappe.db.set_value("CRM Fields Layout", "CRM Lead-Quick Entry", "layout", quick_entry_layout)

    if frappe.db.exists("CRM Fields Layout", "CRM Lead-Side Panel"):
        frappe.db.set_value("CRM Fields Layout", "CRM Lead-Side Panel", "layout", side_panel_layout)

    frappe.db.commit()
