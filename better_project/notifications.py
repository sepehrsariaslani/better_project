# فایل: better_project/notifications.py

import frappe
from frappe import _

def get_notification_config():
    """Return notification config for this app"""
    return {
        # Example: Add notification settings for a doctype
        # "DocType Name": {
        #     "fieldname": "filter_value",
        #     "date_fieldname": "some_date_field"
        # },
        # Or a custom method
        # "Another DocType": "better_project.notifications.get_custom_notifications"
    }

# Example of a custom notification method (if needed)
# def get_custom_notifications(user):
#     # Fetch custom notifications for the user
#     return []

def get_active_tasks_for_notification():
    """دریافت تسک‌های فعال برای اعلان"""
    try:
        user = frappe.session.user
        employee = frappe.db.get_value("Employee", {"user_id": user})
        
        if not employee:
            return []
            
        active_tasks = frappe.db.sql("""
            SELECT 
                t.name,
                t.subject,
                t.status,
                td.from_time
            FROM `tabTask` t
            JOIN `tabTimesheet Detail` td ON t.name = td.task
            JOIN `tabTimesheet` ts ON td.parent = ts.name
            WHERE td.to_time IS NULL 
            AND ts.employee = %s
            AND t.docstatus = 0
            AND t.status != 'Completed'
            ORDER BY td.from_time DESC
        """, (employee,), as_dict=1)
        
        return [{
            "title": task.subject,
            "message": f"در حال کار روی این تسک از ساعت {frappe.utils.format_datetime(task.from_time, 'HH:mm')}",
            "route": f"/app/task/{task.name}"
        } for task in active_tasks]
        
    except Exception as e:
        frappe.log_error(f"Error in get_active_tasks_for_notification: {str(e)}")
        return [] 