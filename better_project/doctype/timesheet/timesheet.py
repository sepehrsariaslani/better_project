class Timesheet(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.projects.doctype.timesheet_detail.timesheet_detail import TimesheetDetail

		amended_from: DF.Link | None
		base_total_billable_amount: DF.Currency
		base_total_billed_amount: DF.Currency
		base_total_costing_amount: DF.Currency
		company: DF.Link | None
		currency: DF.Link | None
		customer: DF.Link | None
		department: DF.Link | None
		employee: DF.Link | None
		employee_name: DF.Data | None
		end_date: DF.Date | None
		exchange_rate: DF.Float
		naming_series: DF.Literal["TS-.YYYY.-"]
		note: DF.TextEditor | None
		parent_project: DF.Link | None
		per_billed: DF.Percent
		salary_slip: DF.Link | None
		sales_invoice: DF.Link | None
		start_date: DF.Date | None
		status: DF.Literal["Draft", "Submitted", "Billed", "Payslip", "Completed", "Cancelled"]
		time_logs: DF.Table[TimesheetDetail]
		title: DF.Data | None
		total_billable_amount: DF.Currency
		total_billable_hours: DF.Float
		total_billed_amount: DF.Currency
		total_billed_hours: DF.Float
		total_costing_amount: DF.Currency
		total_hours: DF.Float
		user: DF.Link | None
	# end: auto-generated types 