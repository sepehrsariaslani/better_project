# custom_app/api/task_timer.py
import frappe
from frappe.utils import now, get_datetime, now_datetime, time_diff_in_hours, format_duration
from frappe import _
import json
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
        
        # بستن همه Timer های باز این کارمند
        stopped_task = stop_all_active_timers(employee)
        
        # پیدا کردن یا ایجاد Timesheet
        timesheet = get_or_create_timesheet(employee, task_doc.project)
        
        # اضافه کردن Time Log جدید
        timesheet_doc = frappe.get_doc("Timesheet", timesheet)
        timesheet_doc.append("time_logs", {
            "activity_type": get_default_activity_type(),
            "task": task,
            "from_time": now(),
            "description": f"کار روی تسک: {task_doc.subject}"
        })
        
        timesheet_doc.save()
        frappe.db.commit()
        
        result = {"success": True}
        if stopped_task:
            result["stopped_task"] = stopped_task
            
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
        active_log = frappe.db.get_list("Timesheet Detail", 
            filters={
                "task": task,
                "to_time": ["is", "null"],
                "parent": ["in", get_user_timesheets(employee)]
            },
            order_by="creation desc",
            limit=1
        )
        
        if not active_log:
            return {"success": False, "error": "هیچ Timer فعالی برای این تسک پیدا نشد"}
        
        # بستن Time Log
        log_doc = frappe.get_doc("Timesheet Detail", active_log[0].name)
        log_doc.to_time = now()
        
        # محاسبه ساعات کاری
        hours = time_diff_in_hours(log_doc.to_time, log_doc.from_time)
        log_doc.hours = hours
        
        log_doc.save()
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
        task = frappe.get_doc('Task', task_name)
        if not task:
            return {'is_running': False}
            
        # بررسی وجود Time Log فعال
        active_time_log = frappe.get_all(
            'Time Log',
            filters={
                'task': task_name,
                'docstatus': 1,
                'status': 'Active'
            },
            fields=['name', 'from_time'],
            limit=1
        )
        
        if not active_time_log:
            return {'is_running': False}
            
        time_log = active_time_log[0]
        start_time = frappe.utils.get_datetime(time_log.from_time)
        elapsed_time = time_diff_in_hours(now_datetime(), start_time)
        
        return {
            'is_running': True,
            'start_time': start_time.isoformat(),
            'elapsed_time': elapsed_time
        }
    except Exception as e:
        frappe.log_error(f"Error in get_timer_status: {str(e)}")
        return {'is_running': False}

@frappe.whitelist()
def get_task_time_info(task_name):
    """دریافت اطلاعات زمانی یک تسک"""
    try:
        task = frappe.get_doc('Task', task_name)
        if not task:
            return None
            
        # بررسی Time Log فعال
        active_time_log = frappe.get_all(
            'Time Log',
            filters={
                'task': task_name,
                'docstatus': 1,
                'status': 'Active'
            },
            fields=['name', 'from_time'],
            limit=1
        )
        
        # محاسبه مجموع زمان
        total_time = frappe.db.sql("""
            SELECT SUM(hours)
            FROM `tabTime Log`
            WHERE task = %s
            AND docstatus = 1
            AND status = 'Completed'
        """, task_name)[0][0] or 0
        
        result = {
            'is_running': bool(active_time_log),
            'total_time': total_time,
            'total_time_formatted': format_duration(total_time)
        }
        
        if active_time_log:
            time_log = active_time_log[0]
            start_time = frappe.utils.get_datetime(time_log.from_time)
            elapsed_time = time_diff_in_hours(now_datetime(), start_time)
            result.update({
                'start_time': frappe.utils.format_datetime(start_time, 'HH:mm:ss'),
                'elapsed_time': format_duration(elapsed_time)
            })
            
        return result
    except Exception as e:
        frappe.log_error(f"Error in get_task_time_info: {str(e)}")
        return None

@frappe.whitelist()
def get_current_elapsed_time(task_name):
    """دریافت زمان سپری شده فعلی برای یک تسک"""
    try:
        active_time_log = frappe.get_all(
            'Time Log',
            filters={
                'task': task_name,
                'docstatus': 1,
                'status': 'Active'
            },
            fields=['from_time'],
            limit=1
        )
        
        if not active_time_log:
            return '00:00:00'
            
        start_time = frappe.utils.get_datetime(active_time_log[0].from_time)
        elapsed_time = time_diff_in_hours(now_datetime(), start_time)
        
        return format_duration(elapsed_time)
    except Exception as e:
        frappe.log_error(f"Error in get_current_elapsed_time: {str(e)}")
        return '00:00:00'

@frappe.whitelist()
def get_active_task_for_navbar():
    """Get active task timer information for navbar display"""
    try:
        user = frappe.session.user
        employee = get_employee_by_user(user)
        
        if not employee:
            return None
        
        # Find active timesheet detail
        active_log = frappe.db.get_list("Timesheet Detail", 
            filters={
                "to_time": ["is", "null"],
                "parent": ["in", get_user_timesheets(employee)]
            },
            fields=["task", "from_time", "name"],
            order_by="creation desc",
            limit=1
        )
        
        if not active_log:
            return None
            
        task_log = active_log[0]
        task_doc = frappe.get_doc("Task", task_log.task)
        
        # Calculate elapsed time
        from_time = frappe.utils.get_datetime(task_log.from_time)
        elapsed_time = time_diff_in_hours(now_datetime(), from_time)
        elapsed_minutes = round(elapsed_time * 60)
        
        return {
            "task_name": task_log.task,
            "task_subject": task_doc.subject,
            "project": task_doc.project,
            "elapsed_minutes": elapsed_minutes,
            "start_time": frappe.utils.format_datetime(from_time, "HH:mm:ss"),
            "timesheet_detail": task_log.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_active_task_for_navbar: {str(e)}")
        return None

# Helper Functions
def get_employee_by_user(user):
    """Get employee linked to user"""
    return frappe.db.get_value("Employee", {"user_id": user}, "name")

def get_user_timesheets(employee):
    """Get all timesheets for an employee"""
    return frappe.get_all("Timesheet", 
        filters={"employee": employee, "docstatus": ["!=", 2]},
        pluck="name"
    )

def get_default_activity_type():
    """Get default activity type for timesheet"""
    return frappe.db.get_single_value("Projects Settings", "default_activity_type") or "Development"

def stop_all_active_timers(employee):
    """Stop all active timers for an employee"""
    active_logs = frappe.db.get_list("Timesheet Detail",
        filters={
            "to_time": ["is", "null"],
            "parent": ["in", get_user_timesheets(employee)]
        },
        fields=["name", "task", "from_time", "parent"],
        order_by="creation desc"
    )
    
    stopped_task = None
    for log in active_logs:
        timesheet_detail = frappe.get_doc("Timesheet Detail", log.name)
        timesheet_detail.to_time = now()
        timesheet_detail.hours = time_diff_in_hours(timesheet_detail.to_time, timesheet_detail.from_time)
        timesheet_detail.save()
        
        if not stopped_task:
            stopped_task = log.task
            
    if active_logs:
        frappe.db.commit()
        
    return stopped_task

def get_or_create_timesheet(employee, project):
    """Get existing open timesheet or create new one"""
    filters = {
        "employee": employee,
        "start_date": frappe.utils.nowdate(),
        "end_date": frappe.utils.nowdate(),
        "docstatus": 0
    }
    
    timesheet_name = frappe.db.get_value("Timesheet", filters)
    
    if timesheet_name:
        return timesheet_name
        
    timesheet = frappe.get_doc({
        "doctype": "Timesheet",
        "employee": employee,
        "start_date": frappe.utils.nowdate(),
        "end_date": frappe.utils.nowdate(),
        "status": "Draft"
    })
    timesheet.insert()
    
    return timesheet.name