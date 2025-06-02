import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate, time_diff_in_hours, format_duration, now, get_datetime, today
from datetime import timedelta
from erpnext.projects.doctype.timesheet.timesheet import Timesheet
import random

class Task(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Task class initialized with methods:", dir(self))  # Debug print
        
    def validate(self):
        """Validate task before saving"""
        self.validate_task()
        # Skip working hours validation for tasks
        frappe.flags.skip_working_hours_validation = True
    
    def validate_project(self):
        """Validate that task has a project"""
        if not self.project and self.doctype == "Task":
            frappe.throw(_("لطفا یک پروژه برای این تسک انتخاب کنید"))
    
    def validate_active_timer(self):
        """Validate that user doesn't have multiple active timers"""
        if self.is_new():
            return
            
        active_task = frappe.db.sql("""
            SELECT name, subject 
            FROM `tabTask` 
            WHERE docstatus = 0 
            AND status != 'Completed'
            AND _user_tags LIKE %s
            AND name != %s
        """, (f'%{frappe.session.user}%', self.name), as_dict=1)
        
        if active_task:
            frappe.throw(_("شما در حال حاضر یک زمان‌سنج فعال روی تسک '{0}' دارید").format(
                active_task[0].subject
            ))

    def start_timer(self):
        """Start timer for the task"""
        if not self.project:
            frappe.throw(_("لطفا یک پروژه برای این تسک انتخاب کنید"))
            
        # Stop any existing timer
        stopped_task = self.stop_all_active_timers()
        
        # Create or get timesheet
        timesheet = self.get_or_create_timesheet()
        
        # Create time log
        timesheet_doc = frappe.get_doc("Timesheet", timesheet)
        timesheet_doc.append("time_logs", {
            "activity_type": self.get_default_activity_type(),
            "from_time": now_datetime(),
            "to_time": None,
            "task": self.name,
            "project": self.project,
            "description": f"کار روی تسک: {self.subject}"
        })
        timesheet_doc.save()
        
        # Update task
        self.db_set("_user_tags", frappe.session.user)
        frappe.db.commit()
        
        return {
            "success": True,
            "timesheet": timesheet.name,
            "stopped_task": stopped_task
        }
    
    def stop_timer(self):
        """Stop timer for the task"""
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user})
        if not employee:
            return {"success": False, "error": "هیچ کارمندی برای این کاربر پیدا نشد"}
            
        # Find active time log
        active_log = frappe.db.sql("""
            SELECT ts.name as timesheet, td.name as time_log, td.from_time
            FROM `tabTimesheet` ts
            JOIN `tabTimesheet Detail` td ON td.parent = ts.name
            WHERE ts.employee = %s
            AND td.task = %s
            AND td.to_time IS NULL
            AND ts.docstatus = 0
        """, (employee, self.name), as_dict=1)
        
        if not active_log:
            return {"success": False, "has_active_timer": False}
            
        # Update time log
        to_time = now_datetime()
        hours = time_diff_in_hours(to_time, active_log[0].from_time)
        frappe.db.set_value("Timesheet Detail", active_log[0].time_log, {
            "to_time": to_time,
            "hours": hours,
            "billing_hours": hours
        })
        
        # Recalculate and update task's actual_time
        self.update_actual_time_from_timesheets()
        
        frappe.db.commit()
        
        return {"success": True, "has_active_timer": True}
    
    def complete_task(self):
        """Complete the task and stop timer if active"""
        # Try to stop timer if exists
        stop_result = self.stop_timer()
        
        # Complete task regardless of timer status
        self.status = "Completed"
        self.completed_on = getdate()
        self.progress = 100
        
        # Ensure actual_time is updated before saving
        self.update_actual_time_from_timesheets()

        self.save()
        
        return {
            "success": True,
            "timer_stopped": stop_result.get("success", False)
        }
    
    def get_active_timesheet(self):
        """Get active timesheet for current user and project"""
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user})
        if not employee:
            return None
            
        return frappe.db.get_value("Timesheet", {
            "employee": employee,
            "project": self.project,
            "docstatus": 0,
            "start_date": ["<=", getdate()],
            "end_date": [">=", getdate()]
        })
    
    def get_or_create_timesheet(self):
        """Get or create timesheet for current user and project"""
        timesheet = self.get_active_timesheet()
        if timesheet:
            return frappe.get_doc("Timesheet", timesheet)
            
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user})
        if not employee:
            frappe.throw(_("هیچ کارمندی برای این کاربر پیدا نشد"))
            
        timesheet = frappe.get_doc({
            "doctype": "Timesheet",
            "employee": employee,
            "project": self.project,
            "start_date": getdate(),
            "end_date": getdate(),
            "title": f"جدول زمانی {frappe.get_value('Employee', employee, 'employee_name')}",
            "company": frappe.defaults.get_defaults().company,
            "time_logs": [{
                "activity_type": self.get_default_activity_type(),
                "from_time": now_datetime(),
                "to_time": None,
                "hours": 0,
                "description": "زمان‌سنج پیش‌فرض"
            }]
        })
        timesheet.insert()
        return timesheet

    def stop_all_active_timers(self):
        """Stop all active timers for current user"""
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user})
        if not employee:
            return None
            
        # Find all active time logs
        active_logs = frappe.db.sql("""
            SELECT ts.name as timesheet, td.name as time_log, td.task
            FROM `tabTimesheet` ts
            JOIN `tabTimesheet Detail` td ON td.parent = ts.name
            WHERE ts.employee = %s
            AND td.to_time IS NULL
            AND ts.docstatus = 0
        """, (employee,), as_dict=1)
        
        stopped_task = None
        for log in active_logs:
            timesheet = frappe.get_doc("Timesheet", log.timesheet)
            time_log = timesheet.get("time_logs", {"name": log.time_log})[0]
            time_log.to_time = now_datetime()
            time_log.hours = time_diff_in_hours(time_log.to_time, time_log.from_time)
            timesheet.save()
            
            if not stopped_task:
                task_doc = frappe.get_doc("Task", log.task)
                stopped_task = task_doc.subject
        
        frappe.db.commit()
        return stopped_task

    def get_default_activity_type(self):
        """Get default activity type"""
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user})
        if employee:
            activity_type = frappe.db.get_value("Employee", employee, "default_activity_type")
            if activity_type:
                return activity_type
        
        # Fallback to first available activity type
        activity_type = frappe.db.get_value("Activity Type", {}, "name")
        return activity_type or "Task"

    def on_update(self):
        """Handle task updates"""
        self.on_task_update()
        # Reset the flag after update
        frappe.flags.skip_working_hours_validation = False

    def update_actual_time_from_timesheets(self):
        """Calculate total actual time from linked timesheet details and update task"""
        total_actual_time = frappe.db.sql("""
            SELECT SUM(td.hours)
            FROM `tabTimesheet Detail` td
            JOIN `tabTimesheet` ts ON ts.name = td.parent
            WHERE td.task = %s
            AND ts.docstatus = 1 -- Only sum from submitted timesheets
        """, (self.name))[0][0] or 0
        
        self.db_set("actual_time", total_actual_time)
        frappe.db.commit()

@frappe.whitelist()
def start_timer(task_name):
    """API endpoint to start timer"""
    try:
        task = frappe.get_doc("Task", task_name)
        if not task:
            return {"success": False, "error": "تسک مورد نظر یافت نشد"}
            
        # Check if user has permission
        if not frappe.has_permission("Task", "write", task_name):
            return {"success": False, "error": "شما دسترسی لازم برای این عملیات را ندارید"}
            
        return task.start_timer()
    except Exception as e:
        frappe.log_error(f"Error in start_timer: {str(e)}")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def stop_timer(task_name):
    """API endpoint to stop timer"""
    try:
        task = frappe.get_doc("Task", task_name)
        if not task:
            return {"success": False, "error": "تسک مورد نظر یافت نشد"}
            
        # Check if user has permission
        if not frappe.has_permission("Task", "write", task_name):
            return {"success": False, "error": "شما دسترسی لازم برای این عملیات را ندارید"}
            
        return task.stop_timer()
    except Exception as e:
        frappe.log_error(f"Error in stop_timer: {str(e)}")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def complete_task(task_name):
    """API endpoint to complete task"""
    task = frappe.get_doc("Task", task_name)
    return task.complete_task()

@frappe.whitelist()
def get_timer_status(task_name):
    """Get timer status for task"""
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
        
        return {"is_running": len(active_log) > 0}
        
    except Exception as e:
        frappe.log_error(f"خطا در دریافت وضعیت زمان‌سنج: {str(e)}")
        return {"is_running": False}

@frappe.whitelist()
def get_task_time_info(task_name):
    """Get time information for task"""
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
            start_time = get_datetime(active_log[0]["from_time"])
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
def get_current_elapsed_time(task_name):
    """Get current elapsed time for task"""
    try:
        user = frappe.session.user
        employee = frappe.db.get_value("Employee", {"user_id": user})
        
        if not employee:
            return "0 دقیقه"
        
        active_log = frappe.db.get_all("Timesheet Detail",
            filters={
                "task": task_name,
                "to_time": ["is", "null"],
                "parent": ["in", frappe.db.get_list("Timesheet", 
                    filters={"employee": employee}, 
                    pluck="name"
                )]
            },
            fields=["from_time"],
            limit=1
        )
        
        if not active_log:
            return "0 دقیقه"
        
        start_time = get_datetime(active_log[0]["from_time"])
        elapsed_seconds = (get_datetime(now_datetime()) - start_time).total_seconds()
        
        return format_duration(elapsed_seconds)
        
    except Exception as e:
        return "خطا"

@frappe.whitelist()
def get_active_task_for_navbar():
    """Get active task for navbar display"""
    try:
        user = frappe.session.user
        employee = frappe.db.get_value("Employee", {"user_id": user})
        
        if not employee:
            return None
        
        active_logs = frappe.db.sql("""
            SELECT 
                td.task,
                td.from_time,
                t.subject,
                t.name,
                t.status,
                t.progress
            FROM `tabTimesheet Detail` td
            JOIN `tabTask` t ON td.task = t.name
            JOIN `tabTimesheet` ts ON td.parent = ts.name
            WHERE td.to_time IS NULL 
            AND ts.employee = %s
            AND ts.docstatus = 0
            ORDER BY td.from_time DESC
            LIMIT 1
        """, (employee,), as_dict=True)
        
        if not active_logs:
            return None
        
        active_log = active_logs[0]
        start_time = get_datetime(active_log["from_time"])
        elapsed_seconds = (get_datetime(now_datetime()) - start_time).total_seconds()
        
        return {
            "task_name": active_log["task"],
            "task_subject": active_log["subject"],
            "start_time": start_time.strftime("%H:%M:%S"),
            "elapsed_time": format_duration(elapsed_seconds),
            "elapsed_minutes": int(elapsed_seconds // 60),
            "status": active_log["status"],
            "progress": active_log["progress"]
        }
        
    except Exception as e:
        frappe.log_error(f"خطا در دریافت تسک فعال: {str(e)}")
        return None

@frappe.whitelist()
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

def validate_task(doc, method=None):
    """Validate task before save"""
    if not doc.project:
        frappe.throw("تسک باید به یک پروژه متصل باشد")
    
    # بررسی وجود پروژه
    if not frappe.db.exists("Project", doc.project):
        frappe.throw("پروژه انتخاب شده وجود ندارد")
    
    # بررسی وضعیت پروژه
    project_status = frappe.db.get_value("Project", doc.project, "status")
    if project_status == "Completed":
        frappe.throw("تسک نمی‌تواند به یک پروژه تکمیل شده متصل باشد")
    
    # اگر تسک تکمیل شده است
    if doc.status == "Completed":
        # بررسی تایمرهای باز
        active_timers = frappe.db.sql("""
            SELECT ts.name as timesheet, td.name as time_log
            FROM `tabTimesheet` ts
            JOIN `tabTimesheet Detail` td ON td.parent = ts.name
            WHERE td.task = %s
            AND td.to_time IS NULL
            AND ts.docstatus = 0
        """, doc.name, as_dict=1)
        
        if active_timers:
            frappe.throw("قبل از تکمیل تسک، لطفا تایمرهای فعال را متوقف کنید")
        
        # تنظیم تاریخ تکمیل
        if not doc.completed_on:
            doc.completed_on = now()
        
        # تنظیم پیشرفت به 100%
        doc.progress = 100

def on_task_update(doc, method=None):
    """Handle task updates"""
    if doc.status == "Completed":
        # متوقف کردن همه تایمرهای فعال
        active_timers = frappe.db.sql("""
            SELECT ts.name as timesheet, td.name as time_log, td.from_time
            FROM `tabTimesheet` ts
            JOIN `tabTimesheet Detail` td ON td.parent = ts.name
            WHERE td.task = %s
            AND td.to_time IS NULL
            AND ts.docstatus = 0
        """, doc.name, as_dict=1)
        
        for timer in active_timers:
            to_time = now()
            hours = time_diff_in_hours(to_time, timer.from_time)
            frappe.db.set_value("Timesheet Detail", timer.time_log, {
                "to_time": to_time,
                "hours": hours,
                "billing_hours": hours
            })
        
        if active_timers:
            frappe.db.commit()

def on_task_trash(doc, method=None):
    """Handle task deletion"""
    # بررسی وجود تایمرهای فعال
    active_timers = frappe.db.sql("""
        SELECT ts.name as timesheet, td.name as time_log
        FROM `tabTimesheet` ts
        JOIN `tabTimesheet Detail` td ON td.parent = ts.name
        WHERE td.task = %s
        AND td.to_time IS NULL
        AND ts.docstatus = 0
    """, doc.name, as_dict=1)
    
    if active_timers:
        frappe.throw("قبل از حذف تسک، لطفا تایمرهای فعال را متوقف کنید")

@frappe.whitelist()
def get_today_tasks():
    """Get all tasks that user has worked on today"""
    try:
        user = frappe.session.user
        employee = frappe.db.get_value("Employee", {"user_id": user})
        
        if not employee:
            return []
            
        today = getdate()
        tasks = frappe.db.sql("""
            SELECT DISTINCT
                t.name,
                t.subject,
                t.status,
                t.progress,
                t.project,
                p.project_name,
                MAX(td.from_time) as last_activity,
                SUM(td.hours) as total_hours
            FROM `tabTask` t
            JOIN `tabTimesheet Detail` td ON t.name = td.task
            JOIN `tabTimesheet` ts ON td.parent = ts.name
            LEFT JOIN `tabProject` p ON t.project = p.name
            WHERE ts.employee = %s
            AND DATE(td.from_time) = %s
            AND ts.docstatus = 1
            GROUP BY t.name
            ORDER BY last_activity DESC
        """, (employee, today), as_dict=1)
        
        return [{
            "name": task.name,
            "subject": task.subject,
            "status": task.status,
            "progress": task.progress,
            "project": task.project,
            "project_name": task.project_name,
            "last_activity": task.last_activity.strftime("%H:%M:%S"),
            "total_hours": round(task.total_hours, 2)
        } for task in tasks]
        
    except Exception as e:
        frappe.log_error(f"Error in get_today_tasks: {str(e)}")
        return []

@frappe.whitelist()
def get_work_statistics():
    """Get work statistics for the last 7 days"""
    try:
        user = frappe.session.user
        employee = frappe.db.get_value("Employee", {"user_id": user})
        
        if not employee:
            return None
            
        today = getdate()
        week_ago = today - timedelta(days=6)
        
        # Get daily work hours
        daily_stats = frappe.db.sql("""
            SELECT 
                DATE(td.from_time) as date,
                SUM(td.hours) as total_hours,
                COUNT(DISTINCT td.task) as task_count
            FROM `tabTimesheet Detail` td
            JOIN `tabTimesheet` ts ON td.parent = ts.name
            WHERE ts.employee = %s
            AND DATE(td.from_time) BETWEEN %s AND %s
            AND ts.docstatus = 1
            GROUP BY DATE(td.from_time)
            ORDER BY date
        """, (employee, week_ago, today), as_dict=1)
        
        # Get today's total hours
        today_hours = frappe.db.sql("""
            SELECT SUM(td.hours) as total_hours
            FROM `tabTimesheet Detail` td
            JOIN `tabTimesheet` ts ON td.parent = ts.name
            WHERE ts.employee = %s
            AND DATE(td.from_time) = %s
            AND ts.docstatus = 1
        """, (employee, today))[0][0] or 0
        
        # Get week's total hours
        week_hours = frappe.db.sql("""
            SELECT SUM(td.hours) as total_hours
            FROM `tabTimesheet Detail` td
            JOIN `tabTimesheet` ts ON td.parent = ts.name
            WHERE ts.employee = %s
            AND DATE(td.from_time) BETWEEN %s AND %s
            AND ts.docstatus = 1
        """, (employee, week_ago, today))[0][0] or 0
        
        # Format daily stats
        formatted_stats = []
        for i in range(7):
            date = today - timedelta(days=i)
            day_stat = next((stat for stat in daily_stats if stat.date == date), None)
            formatted_stats.append({
                "date": date.strftime("%Y-%m-%d"),
                "day": date.strftime("%a"),
                "hours": round(day_stat.total_hours, 2) if day_stat else 0,
                "task_count": day_stat.task_count if day_stat else 0
            })
        
        return {
            "today_hours": round(today_hours, 2),
            "week_hours": round(week_hours, 2),
            "daily_stats": formatted_stats[::-1]  # Reverse to show oldest first
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_work_statistics: {str(e)}")
        return None

@frappe.whitelist()
def get_overdue_tasks():
    """Get tasks that have passed their expected start date"""
    try:
        user = frappe.session.user
        employee = frappe.db.get_value("Employee", {"user_id": user})
        
        if not employee:
            return []
            
        today = getdate()
        overdue_tasks = frappe.db.sql("""
            SELECT 
                t.name,
                t.subject,
                t.status,
                t.progress,
                t.project,
                p.project_name,
                t.exp_start_date,
                DATEDIFF(%s, t.exp_start_date) as days_overdue
            FROM `tabTask` t
            LEFT JOIN `tabProject` p ON t.project = p.name
            WHERE t.exp_start_date < %s
            AND t.status != 'Completed'
            AND (
                t.assigned_to = %s
                OR t._user_tags LIKE %s
            )
            ORDER BY t.exp_start_date ASC
        """, (today, today, user, f'%{user}%'), as_dict=1)
        
        return [{
            "name": task.name,
            "subject": task.subject,
            "status": task.status,
            "progress": task.progress,
            "project": task.project,
            "project_name": task.project_name,
            "exp_start_date": task.exp_start_date.strftime("%Y-%m-%d"),
            "days_overdue": task.days_overdue
        } for task in overdue_tasks]
        
    except Exception as e:
        frappe.log_error(f"Error in get_overdue_tasks: {str(e)}")
        return []

@frappe.whitelist()
def get_available_tasks():
    """Get tasks that can be started"""
    try:
        user = frappe.session.user
        employee = frappe.db.get_value("Employee", {"user_id": user})
        
        if not employee:
            return []
            
        # Get tasks that are not completed and not already being worked on
        tasks = frappe.db.sql("""
            SELECT 
                t.name,
                t.subject,
                t.status,
                t.progress,
                t.project,
                p.project_name,
                t.priority,
                t.exp_start_date,
                t.exp_end_date
            FROM `tabTask` t
            LEFT JOIN `tabProject` p ON t.project = p.name
            WHERE t.status != 'Completed'
            AND (
                t.assigned_to = %s
                OR t._user_tags LIKE %s
            )
            AND NOT EXISTS (
                SELECT 1 
                FROM `tabTimesheet Detail` td
                JOIN `tabTimesheet` ts ON td.parent = ts.name
                WHERE td.task = t.name
                AND td.to_time IS NULL
                AND ts.employee = %s
                AND ts.docstatus = 0
            )
            ORDER BY 
                CASE t.priority
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    WHEN 'Low' THEN 3
                    ELSE 4
                END,
                t.exp_start_date ASC,
                t.creation DESC
        """, (user, f'%{user}%', employee), as_dict=1)
        
        return [{
            "name": task.name,
            "subject": task.subject,
            "status": task.status,
            "progress": task.progress,
            "project": task.project,
            "project_name": task.project_name,
            "priority": task.priority,
            "exp_start_date": task.exp_start_date.strftime("%Y-%m-%d") if task.exp_start_date else None,
            "exp_end_date": task.exp_end_date.strftime("%Y-%m-%d") if task.exp_end_date else None
        } for task in tasks]
        
    except Exception as e:
        frappe.log_error(f"Error in get_available_tasks: {str(e)}")
        return []

@frappe.whitelist()
def get_current_employees_status():
	"""Get current active tasks for all employees"""
	active_statuses = frappe.db.sql("""
		SELECT
			task.name as task_name,
			task.subject as task_subject,
			emp.employee_name as employee_name,
			user.user_image as user_image,
			td.from_time as start_time
		FROM `tabTimesheet` ts
		JOIN `tabTimesheet Detail` td ON td.parent = ts.name
		JOIN `tabTask` task ON task.name = td.task
		JOIN `tabEmployee` emp ON emp.name = ts.employee
		JOIN `tabUser` user ON user.name = emp.user_id
		WHERE ts.docstatus = 0
		AND td.to_time IS NULL
	""", as_dict=1)

	return active_statuses

@frappe.whitelist()
def get_my_overdue_tasks():
	"""Get overdue tasks for the current user"""
	user = frappe.session.user
	today = getdate()

	overdue_tasks = frappe.db.sql("""
		SELECT
			name,
			subject,
			project,
			exp_end_date,
			progress,
			DATEDIFF(%s, exp_end_date) as days_overdue
		FROM `tabTask`
		WHERE assigned_to LIKE %s
		AND exp_end_date < %s
		AND status NOT IN ('Completed', 'Cancelled')
		ORDER BY exp_end_date ASC
	""", (today, f'%{user}%', today), as_dict=1)

	return overdue_tasks

@frappe.whitelist()
def get_my_today_tasks():
	"""Get tasks worked on by the current user today"""
	user = frappe.session.user
	today_start = get_datetime(today()).replace(hour=0, minute=0, second=0, microsecond=0)
	today_end = get_datetime(today()).replace(hour=23, minute=59, second=59, microsecond=999999)

	today_tasks = frappe.db.sql("""
		SELECT
			task.name,
			task.subject,
			task.project,
			task.progress,
			SUM(td.hours) as total_hours_today,
			MAX(td.to_time) as last_activity_time,
            (SELECT COUNT(*) FROM `tabTimesheet Detail` WHERE task = task.name AND to_time IS NULL AND parent = ts.name) > 0 as is_active
		FROM `tabTimesheet Detail` td
		JOIN `tabTimesheet` ts ON ts.name = td.parent
		JOIN `tabTask` task ON task.name = td.task
		JOIN `tabEmployee` emp ON emp.name = ts.employee
		WHERE emp.user_id = %s
		AND td.from_time BETWEEN %s AND %s
		GROUP BY task.name, task.subject, task.project, task.progress
		ORDER BY last_activity_time DESC
	""", (user, today_start, today_end), as_dict=1)

	# Format total hours and last activity time
	for task in today_tasks:
		task['total_time'] = frappe.utils.format_duration(task['total_hours_today'] * 3600)
		task['last_activity'] = frappe.utils.get_datetime_str(task['last_activity_time']).split(' ')[1] if task['last_activity_time'] else '--:--'

	return today_tasks

@frappe.whitelist()
def get_my_today_time_data():
	"""Get time data for tasks worked on by the current user today for charting"""
	try:
		user = frappe.session.user
		employee = frappe.db.get_value("Employee", {"user_id": user})

		if not employee:
			return []

		today_start = get_datetime(today()).replace(hour=0, minute=0, second=0, microsecond=0)
		today_end = get_datetime(today()).replace(hour=23, minute=59, second=59, microsecond=999999)

		time_data = frappe.db.sql("""
			SELECT
				task.name as task_name,
				task.subject as task_subject,
				task.project,
				p.project_name,
				p.color as project_color,
				SUM(td.hours) as total_hours
			FROM `tabTimesheet Detail` td
			JOIN `tabTimesheet` ts ON ts.name = td.parent
			JOIN `tabTask` task ON task.name = td.task
			LEFT JOIN `tabProject` p ON task.project = p.name
			JOIN `tabEmployee` emp ON emp.name = ts.employee
			WHERE emp.user_id = %s
			AND td.from_time BETWEEN %s AND %s
			GROUP BY task.name, task.subject, task.project, p.project_name, p.color
			ORDER BY total_hours DESC
		""", (user, today_start, today_end), as_dict=1)

		# Convert hours to float for chart and add formatted time
		for item in time_data:
			item['hours'] = float(item['total_hours'])
			item['total_time_formatted'] = format_duration(item['total_hours'] * 3600)
			if not item.get('project_color'):
				item['project_color'] = '#6c757d'

		return time_data

	except Exception as e:
		frappe.log_error(f"Error in get_my_today_time_data: {str(e)}")
		return []

@frappe.whitelist()
def get_my_daily_project_time_data():
    """Get daily time data per project for the last 7 days for the current user"""
    try:
        user = frappe.session.user
        employee = frappe.db.get_value("Employee", {"user_id": user})

        if not employee:
            frappe.log_error("Employee not found for user: " + user, "get_my_daily_project_time_data")
            return []

        today = getdate()
        week_ago = today - timedelta(days=6)
        
        # Log only the date range, not the full data
        frappe.log_error(f"Fetching daily project time data for employee: {employee}, date range: {week_ago} to {today}", "get_my_daily_project_time_data")

        time_data = frappe.db.sql("""
            SELECT
                DATE(td.from_time) as work_date,
                t.project,
                p.project_name,
                p.color,
                SUM(td.hours) as total_hours
            FROM `tabTimesheet Detail` td
            JOIN `tabTimesheet` ts ON ts.name = td.parent
            JOIN `tabTask` t ON t.name = td.task
            LEFT JOIN `tabProject` p ON t.project = p.name
            JOIN `tabEmployee` emp ON emp.name = ts.employee
            WHERE emp.user_id = %s
            AND DATE(td.from_time) BETWEEN %s AND %s
            AND ts.docstatus = 1
            GROUP BY 1, t.project, p.project_name, p.color
            ORDER BY work_date ASC, t.project ASC
        """, (user, week_ago, today), as_dict=1)
        
        # Log only the count of records found
        frappe.log_error(f"Found {len(time_data)} time records for employee {employee}", "get_my_daily_project_time_data")

        # Convert hours to float and add default color if missing
        for item in time_data:
            item['total_hours'] = float(item['total_hours'])
            if not item.get('color'):
                # Assign a random color (or a predefined fallback) if project has no color
                item['color'] = '#' + '%06x' % random.randint(0, 0xFFFFFF)

        return time_data

    except Exception as e:
        frappe.log_error(f"Error in get_my_daily_project_time_data: {str(e)}", "get_my_daily_project_time_data")
        return []

@frappe.whitelist()
def test_task_methods(task_name):
    """Test method to verify Task class methods"""
    try:
        task = frappe.get_doc("Task", task_name)
        print("Task object methods:", dir(task))  # Debug print
        print("Task object dict:", task.__dict__)  # Debug print
        return {
            "success": True,
            "methods": dir(task),
            "has_start_timer": hasattr(task, 'start_timer'),
            "has_stop_timer": hasattr(task, 'stop_timer')
        }
    except Exception as e:
        frappe.log_error(f"Error in test_task_methods: {str(e)}")
        return {"success": False, "error": str(e)} 