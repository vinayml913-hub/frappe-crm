import frappe
from frappe.model.document import Document

class PBSDeliveryOrder(Document):
    def before_save(self):
        if self.qty and self.rate:
            self.amount = self.qty * self.rate
