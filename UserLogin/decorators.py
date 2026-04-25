from django.shortcuts import redirect

def student_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'student':
            return redirect('landing')
        return view_func(request, *args, **kwargs)
    return wrapper

def lecturer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'lecturer':
            return redirect('landing')
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'admin':
            return redirect('landing')
        return view_func(request, *args, **kwargs)
    return wrapper
