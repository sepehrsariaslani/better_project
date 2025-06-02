import frappe

def execute():
    """Add default_activity_type field to Employee table"""
    if not frappe.db.has_column("Employee", "default_activity_type"):
        frappe.db.sql("""
            ALTER TABLE `tabEmployee`
            ADD COLUMN `default_activity_type` varchar(140)
        """)
        frappe.db.commit() 