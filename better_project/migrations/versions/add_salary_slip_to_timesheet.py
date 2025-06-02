# Copyright (c) 2024, Sepehr Sariaslani and Contributors
# License: MIT. See LICENSE

import frappe

def execute():
    """Add salary_slip field to Timesheet doctype"""
    if not frappe.db.exists("DocField", {"parent": "Timesheet", "fieldname": "salary_slip"}):
        frappe.get_doc({
            "doctype": "DocField",
            "parent": "Timesheet",
            "parentfield": "fields",
            "parenttype": "DocType",
            "fieldname": "salary_slip",
            "fieldtype": "Link",
            "in_list_view": 0,
            "label": "Salary Slip",
            "options": "Salary Slip",
            "reqd": 0,
            "search_index": 0,
            "translatable": 0,
            "unique": 0
        }).insert() 