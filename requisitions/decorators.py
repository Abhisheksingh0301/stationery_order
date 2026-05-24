from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def department_required(view_func):
    """Redirect users who have no Department record assigned."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.user.is_staff:
            return redirect("report_list")
        if not hasattr(request.user, "department"):
            messages.error(request, "Your account has no department assigned. Contact an administrator.")
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped
