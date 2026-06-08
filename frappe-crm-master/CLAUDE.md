# PBS CRM — Project Guide for Claude

## Project Overview
PBS CRM is a customized Frappe CRM built for **Pioneer Business Solutions**.
- **App Name:** PBS CRM
- **Frappe Cloud URL:** https://pbscrm.frappe.cloud/crm
- **GitHub Repo:** https://github.com/krupasagar369/frappe-crm (vinayml913-hub/frappe-crm)
- **Stack:** Python (Frappe Framework) + Vue 3 (Vite) + MariaDB

---

## Project Structure
```
frappe-crm/
├── crm/                          # Backend (Python/Frappe)
│   ├── api/                      # Whitelisted API endpoints
│   │   ├── __init__.py           # check_app_permission() - role access
│   │   ├── session.py            # CRM_ALLOWED_ROLES, get_users()
│   │   ├── dashboard.py          # Dashboard charts & metrics
│   │   ├── notifications.py      # get_notifications(), mark_as_read()
│   │   ├── sales_order.py        # get_sales_orders() API
│   │   └── event.py              # Calendar event notifications
│   ├── fcrm/doctype/             # Frappe DocTypes (DB schema)
│   │   ├── crm_lead/             # Lead DocType
│   │   ├── crm_deal/             # Deal DocType
│   │   ├── pbs_sales_order/      # Sales Order DocType
│   │   └── pbs_delivery_order/   # Delivery Order child DocType
│   ├── hooks.py                  # Frappe hooks (doc_events, scheduler)
│   ├── install.py                # Default layouts & setup
│   └── patches/v1_0/             # DB migration patches
├── frontend/src/                 # Frontend (Vue 3)
│   ├── pages/                    # Page components
│   │   ├── Dashboard.vue         # Report/Dashboard page
│   │   ├── Leads.vue             # Leads list
│   │   ├── Deals.vue             # Deals list
│   │   ├── SalesOrders.vue       # Sales Orders page
│   │   └── Organization.vue      # Client page
│   ├── components/
│   │   ├── Layouts/
│   │   │   ├── AppSidebar.vue    # Main sidebar navigation
│   │   │   └── DesktopLayout.vue
│   │   ├── Modals/
│   │   │   └── LeadModal.vue     # Create Lead modal
│   │   ├── Settings/
│   │   │   ├── Users.vue         # User management
│   │   │   └── InviteUserPage.vue
│   │   ├── Icons/
│   │   │   └── SalesOrderIcon.vue
│   │   ├── GlobalSearch.vue      # Global search bar
│   │   └── Notifications.vue     # Notification panel
│   ├── stores/                   # Pinia stores
│   │   ├── notifications.js
│   │   └── views.js
│   └── router.js                 # Vue Router
└── docker/
    ├── docker-compose.yml        # Local Docker setup
    └── init.sh                   # Container init script
```

---

## Custom Changes Made (vs Original Frappe CRM)

### Branding
- App name: **PBS CRM** (Pioneer Business Solutions)
- Logo: `pbslogo.png` uploaded via CRM Settings → Branding

### Sidebar Labels Changed
| Original | Changed To |
|---|---|
| Organizations | Client |
| Dashboard | Report |

### Roles Added
| Role | Access |
|---|---|
| System Manager | Full admin access |
| Sales Manager | All leads & deals, reports |
| Sales User | Own leads & deals only |
| Solution Manager | Own leads only, no deals |

**Files to update when adding new roles:**
- `crm/api/__init__.py` — `check_app_permission()`
- `crm/api/session.py` — `CRM_ALLOWED_ROLES`, `get_users()`
- `frontend/src/components/Settings/Users.vue` — `roleMap`
- `frontend/src/components/Settings/InviteUserPage.vue` — `roleOptions`

### Fields Added
- **CRM Lead:** `description` (Long Text) — in Create modal + Side Panel
- **CRM Lead:** `organization` label changed to **Account Name**, made mandatory
- **CRM Lead:** `email` and `mobile_no` made mandatory

### New Features
- **Global Search** — `GlobalSearch.vue` in sidebar (searches Leads, Deals, Contacts)
- **Sales Orders page** — auto-created when Deal is marked **Won**
- **Delivery Orders** — child table inside Sales Orders with fields:
  Product Code, Item, Type, Qty, Rate, Amount, Start/End Date,
  DO Number, Account, Sales Manager, Account Manager, Delivery Person, Trainers, Status

---

## Key Business Rules
1. **Sales Order auto-creation:** When `CRM Deal.status = "Won"` → `create_sales_order_from_deal()` fires via `hooks.py`
2. **Currency:** INR (₹) — set in Frappe System Settings → Default Currency → INR
3. **Notifications:** Task assignments and mentions show in notification panel

---

## Deployment (Frappe Cloud)
```
GitHub push → Frappe Cloud Dashboard → Benches → PBSCRM → Deploy → Update
```
After deploy with DocType changes:
- Migration runs automatically on Frappe Cloud

## Local Development (Docker)
```bash
cd docker
docker compose up -d
docker compose exec frappe bash -c "cd frappe-bench && bench --site crm.localhost migrate"
docker compose exec frappe bash -c "cd frappe-bench && bench build --app crm"
# Open: http://localhost:8000/crm
```

---

## Common File Locations for Changes

| Task | File |
|---|---|
| Add new sidebar menu item | `frontend/src/components/Layouts/AppSidebar.vue` |
| Add new role access | `crm/api/__init__.py` + `crm/api/session.py` |
| Change field in Lead form | `crm/fcrm/doctype/crm_lead/crm_lead.json` |
| Change Lead create modal fields | `frontend/src/components/Modals/LeadModal.vue` |
| Change layout panels | Frappe Desk → CRM Fields Layout |
| Add DB migration | `crm/patches/v1_0/` + `crm/patches.txt` |
| Change currency symbol | `frontend/src/utils/numberFormat.js` + `crm/api/session.py` |
| Notification logic | `crm/api/notifications.py` |
| Sales Order creation | `crm/fcrm/doctype/pbs_sales_order/pbs_sales_order.py` |
