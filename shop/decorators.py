from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def get_role(user):
    # superuser is always admin, others use the role saved in staff table
    if user.is_superuser:
        return 'admin'
    try:
        return user.staff.role
    except Exception:
        return 'staff'


def is_admin(user):
    return get_role(user) == 'admin'


def admin_required(view_function):
    @wraps(view_function)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not is_admin(request.user):
            messages.error(request, 'Only admin can open that page')
            return redirect('billing')
        return view_function(request, *args, **kwargs)
    return wrapper
