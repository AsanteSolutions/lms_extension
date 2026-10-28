import frappe
from frappe.utils import add_to_date, get_datetime


def execute():
	"""Move custom_due_date onto LMS's own assignment scheduling, which replaces it.

	LMS requires a Schedule Start before the Schedule End whenever scheduling is
	enabled, so the assignment is treated as open from when it was created.
	"""
	if not frappe.db.has_column("LMS Assignment", "custom_due_date"):
		return
	if not frappe.db.has_column("LMS Assignment", "schedule_end"):
		return

	assignments = frappe.get_all(
		"LMS Assignment",
		filters={"custom_due_date": ["is", "set"], "enable_scheduling": 0},
		fields=["name", "creation", "custom_due_date"],
	)

	for assignment in assignments:
		due_date = get_datetime(assignment.custom_due_date)
		start = min(get_datetime(assignment.creation), add_to_date(due_date, minutes=-1))
		frappe.db.set_value(
			"LMS Assignment",
			assignment.name,
			{"enable_scheduling": 1, "schedule_start": start, "schedule_end": due_date},
			update_modified=False,
		)
