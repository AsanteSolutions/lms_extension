import frappe


def show_custom_signup():
	"""Copy of lms.plugins.show_custom_signup that serves this app's signup form,
	which loads the signup-select bundle from lms_extension's assets."""
	settings = frappe.get_single("LMS Settings")
	if settings.custom_signup_content or settings.user_category:
		return "lms_extension/templates/signup-form.html"
	return "frappe/templates/signup.html"
