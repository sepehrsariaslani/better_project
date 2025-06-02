# better_project/api/task_timer.py
import frappe
from frappe.utils import now, get_datetime, now_datetime, time_diff_in_hours, format_duration
from frappe import _
from better_project.doctype.task.task import Task

@frappe.whitelist()
def start_timer(task):
    """شروع Timer برای یک Task"""
    try:
        user = frappe.session.user
        employee = get_employee_by_user(user)
        
        if not employee:
            return {"success": False, "error": "کارمند مرتبط با این کاربر پیدا نشد"}
        
        task_doc = frappe.get_doc("Task", task)
        
        if not task_doc.project:
            return {"success": False, "error": "این تسک باید به یک پروژه متصل باشد"}
        
        # بررسی و بستن همه Timer های فعال این کارمند
        active_timers = frappe.db.sql("""
            SELECT ts.name as timesheet, td.name as time_log, td.task, t.subject
            FROM `tabTimesheet` ts
            JOIN `tabTimesheet Detail` td ON td.parent = ts.name
            JOIN `tabTask` t ON td.task = t.name
            WHERE ts.employee = %s
            AND td.to_time IS NULL
            AND ts.docstatus = 0
            ORDER BY td.creation DESC
        """, (employee,), as_dict=1)
        
        stopped_tasks = []
        for timer in active_timers:
            # بستن تایمر با استفاده از direct database update
            frappe.db.set_value("Timesheet Detail", timer.time_log, {
                "to_time": now(),
                "hours": time_diff_in_hours(now(), timer.from_time)
            })
            stopped_tasks.append({
                "task": timer.task,
                "subject": timer.subject
            })
        
        if stopped_tasks:
            frappe.db.commit()
        
        # پیدا کردن یا ایجاد Timesheet
        timesheet = get_or_create_timesheet(employee, task_doc.project)
        
        # اضافه کردن Time Log جدید با استفاده از direct database update
        time_log = frappe.get_doc({
            "doctype": "Timesheet Detail",
            "parent": timesheet,
            "parentfield": "time_logs",
            "parenttype": "Timesheet",
            "activity_type": get_default_activity_type(),
            "task": task,
            "project": task_doc.project,
            "from_time": now(),
            "description": f"کار روی تسک: {task_doc.subject}",
            "is_billable": task_doc.is_billable if hasattr(task_doc, "is_billable") else 0,
            "billing_hours": 0,
            "billing_amount": 0
        })
        time_log.insert()
        frappe.db.commit()
        
        result = {
            "success": True,
            "stopped_tasks": stopped_tasks
        }
        
        return result
        
    except Exception as e:
        frappe.log_error(f"خطا در شروع Timer: {str(e)}")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def stop_timer(task):
    """توقف Timer برای یک Task"""
    try:
        user = frappe.session.user
        employee = get_employee_by_user(user)
        
        if not employee:
            return {"success": False, "error": "کارمند مرتبط با این کاربر پیدا نشد"}
        
        # پیدا کردن Time Log فعال برای این Task
        active_log = frappe.db.sql("""
            SELECT ts.name as timesheet, td.name as time_log, td.from_time, td.project
            FROM `tabTimesheet` ts
            JOIN `tabTimesheet Detail` td ON td.parent = ts.name
            WHERE ts.employee = %s
            AND td.task = %s
            AND td.to_time IS NULL
            AND ts.docstatus = 0
            ORDER BY td.creation DESC
            LIMIT 1
        """, (employee, task), as_dict=1)
        
        if not active_log:
            return {"success": False, "error": "هیچ Timer فعالی برای این تسک پیدا نشد"}
        
        # بستن Time Log با استفاده از direct database update
        log = active_log[0]
        to_time = now()
        hours = time_diff_in_hours(to_time, log.from_time)
        
        frappe.db.set_value("Timesheet Detail", log.time_log, {
            "to_time": to_time,
            "hours": hours,
            "billing_hours": hours
        })
        frappe.db.commit()
        
        return {"success": True}
        
    except Exception as e:
        frappe.log_error(f"خطا در توقف Timer: {str(e)}")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def complete_task(task):
    """تکمیل Task و بستن Timer"""
    try:
        # ابتدا Timer را متوقف کن
        stop_result = stop_timer(task)
        if not stop_result.get("success"):
            return stop_result
        
        # تکمیل Task
        task_doc = frappe.get_doc("Task", task)
        task_doc.status = "Completed"
        task_doc.completed_on = now()
        task_doc.progress = 100
        task_doc.save()
        
        frappe.db.commit()
        
        return {"success": True}
        
    except Exception as e:
        frappe.log_error(f"خطا در تکمیل Task: {str(e)}")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_timer_status(task_name):
    """دریافت وضعیت زمان‌سنج برای یک تسک"""
    try:
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user})
        if not employee:
            return {"is_running": False}
        
        active_log = frappe.db.sql("""
            SELECT td.from_time
            FROM `tabTimesheet` ts
            JOIN `tabTimesheet Detail` td ON td.parent = ts.name
            WHERE ts.employee = %s
            AND td.task = %s
            AND td.to_time IS NULL
            AND ts.docstatus = 0
            LIMIT 1
        """, (employee, task_name), as_dict=1)
        
        if not active_log:
            return {"is_running": False}
            
        start_time = get_datetime(active_log[0].from_time)
        elapsed_time = time_diff_in_hours(now_datetime(), start_time)
        
        return {
            "is_running": True,
            "start_time": start_time.isoformat(),
            "elapsed_time": elapsed_time
        }
    except Exception as e:
        frappe.log_error(f"Error in get_timer_status: {str(e)}")
        return {"is_running": False}

@frappe.whitelist()
def get_task_time_info(task_name):
    """دریافت اطلاعات زمانی یک تسک"""
    try:
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user})
        if not employee:
            return None
        
        # Active time log
        active_log = frappe.db.sql("""
            SELECT td.from_time
            FROM `tabTimesheet` ts
            JOIN `tabTimesheet Detail` td ON td.parent = ts.name
            WHERE ts.employee = %s
            AND td.task = %s
            AND td.to_time IS NULL
            AND ts.docstatus = 0
            LIMIT 1
        """, (employee, task_name), as_dict=1)
        
        # Total time
        total_hours = frappe.db.sql("""
            SELECT SUM(td.hours) as total_hours
            FROM `tabTimesheet` ts
            JOIN `tabTimesheet Detail` td ON td.parent = ts.name
            WHERE ts.employee = %s
            AND td.task = %s
            AND ts.docstatus = 1
        """, (employee, task_name))[0][0] or 0
        
        result = {
            "total_time": total_hours,
            "total_time_formatted": format_duration(total_hours * 3600) if total_hours else "0 دقیقه",
            "is_running": len(active_log) > 0
        }
        
        if active_log:
            start_time = get_datetime(active_log[0].from_time)
            elapsed_seconds = (get_datetime(now_datetime()) - start_time).total_seconds()
            
            result.update({
                "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
                "elapsed_time": format_duration(elapsed_seconds)
            })
        
        return result
        
    except Exception as e:
        frappe.log_error(f"خطا در دریافت اطلاعات زمانی: {str(e)}")
        return None

@frappe.whitelist()
def get_active_task_for_navbar():
    """Get active task timer information for navbar display"""
    try:
        user = frappe.session.user
        employee = get_employee_by_user(user)
        
        if not employee:
            return None
        
        # Find active timesheet detail
        active_log = frappe.db.sql("""
            SELECT 
                td.task,
                td.from_time,
                td.name as time_log,
                ts.name as timesheet,
                t.subject,
                t.progress
            FROM `tabTimesheet` ts
            JOIN `tabTimesheet Detail` td ON td.parent = ts.name
            JOIN `tabTask` t ON td.task = t.name
            WHERE ts.employee = %s
            AND td.to_time IS NULL
            AND ts.docstatus = 0
            ORDER BY td.creation DESC
            LIMIT 1
        """, (employee,), as_dict=1)
        
        if not active_log:
            return None
            
        task_log = active_log[0]
        start_time = get_datetime(task_log.from_time)
        elapsed_time = time_diff_in_hours(now_datetime(), start_time)
        elapsed_minutes = int(elapsed_time * 60)
        
        return {
            "task_name": task_log.task,
            "task_subject": task_log.subject,
            "project": task_log.project,
            "start_time": frappe.utils.format_datetime(start_time, "HH:mm:ss"),
            "elapsed_time": format_duration(elapsed_time),
            "elapsed_minutes": elapsed_minutes,
            "progress": task_log.progress or 0
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_active_task_for_navbar: {str(e)}")
        return None

# Helper Functions
def get_employee_by_user(user):
    """Get employee linked to user"""
    employee = frappe.db.get_value("Employee", {"user_id": user})
    return employee

def get_user_timesheets(employee):
    """Get all timesheets for an employee"""
    return frappe.db.get_list("Timesheet",
        filters={"employee": employee},
        pluck="name"
    )

def get_default_activity_type():
    """Get default activity type for time logs"""
    employee = get_employee_by_user(frappe.session.user)
    if employee:
        activity_type = frappe.db.get_value("Employee", employee, "default_activity_type")
        if not activity_type:
            frappe.throw("نوع فعالیت پیش‌فرض برای کارمند تنظیم نشده است. لطفا در پروفایل کارمند، نوع فعالیت پیش‌فرض را تنظیم کنید.")
        return activity_type
    
    # Fallback to first available activity type
    activity_type = frappe.db.get_value("Activity Type", {}, "name")
    if not activity_type:
        frappe.throw("هیچ نوع فعالیتی در سیستم تعریف نشده است. لطفا ابتدا نوع فعالیت‌ها را تعریف کنید.")
    return activity_type

def stop_all_active_timers(employee):
    """Stop all active timers for an employee"""
    active_logs = frappe.db.sql("""
        SELECT ts.name as timesheet, td.name as time_log, td.task
        FROM `tabTimesheet` ts
        JOIN `tabTimesheet Detail` td ON td.parent = ts.name
        WHERE ts.employee = %s
        AND td.to_time IS NULL
        AND ts.docstatus = 0
        ORDER BY td.creation DESC
    """, (employee,), as_dict=1)
    
    stopped_task = None
    for log in active_logs:
        # Get the timesheet and time log
        timesheet = frappe.get_doc("Timesheet", log.timesheet)
        time_log = None
        for tl in timesheet.time_logs:
            if tl.name == log.time_log:
                time_log = tl
                break
        
        if time_log:
            # Update time log directly in database to avoid validation
            frappe.db.set_value("Timesheet Detail", time_log.name, {
                "to_time": now(),
                "hours": time_diff_in_hours(now(), time_log.from_time)
            })
            
            if not stopped_task and log.task:
                task_doc = frappe.get_doc("Task", log.task)
                stopped_task = task_doc.subject
    
    if active_logs:
        frappe.db.commit()
    
    return stopped_task

def get_or_create_timesheet(employee, project):
    """Get or create a timesheet for today"""
    today = now_datetime().date()
    
    # Try to find existing timesheet
    timesheet = frappe.db.get_list("Timesheet",
        filters={
            "employee": employee,
            "start_date": ["<=", today],
            "end_date": [">=", today],
            "docstatus": ["!=", 2]
        },
        order_by="creation desc",
        limit=1
    )
    
    if timesheet:
        return timesheet[0].name
    
    # Create new timesheet with a default time log
    timesheet_doc = frappe.get_doc({
        "doctype": "Timesheet",
        "employee": employee,
        "project": project,
        "start_date": today,
        "end_date": today,
        "company": frappe.defaults.get_defaults().company,
        "time_logs": [{
            "activity_type": get_default_activity_type(),
            "from_time": now(),
            "to_time": None,
            "hours": 0,
            "description": "زمان‌سنج پیش‌فرض"
        }]
    })
    
    timesheet_doc.insert()
    frappe.db.commit()
    
    return timesheet_doc.name 