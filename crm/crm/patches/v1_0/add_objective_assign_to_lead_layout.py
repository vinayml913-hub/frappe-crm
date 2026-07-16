import frappe

def execute():
    quick_entry = frappe.db.get_value(
        "CRM Fields Layout", "CRM Lead-Quick Entry", "layout"
    )
    if not quick_entry:
        return

    import json
    layout = json.loads(quick_entry)

    # Add new section with objective and assign_to
    layout.append({
        "name": "extra_section",
        "columns": [
            {"name": "column_OBJ", "fields": ["objective"]},
            {"name": "column_ASN", "fields": ["assign_to"]}
        ]
    })

    frappe.db.set_value(
        "CRM Fields Layout",
        "CRM Lead-Quick Entry",
        "layout",
        json.dumps(layout)
    )
    frappe.db.commit()
