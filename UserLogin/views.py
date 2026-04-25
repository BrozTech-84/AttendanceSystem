from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from .forms import RegistrationForm, LoginForm
from .models import Program 

User = get_user_model()

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)

            # Decide role automatically if you want
            email = form.cleaned_data.get('email')
            if email.endswith('@lecturer.university.ac.ke'):
                user.role = 'lecturer'
            elif email.endswith('@student.university.ac.ke'):
                user.role = 'student'
            else:
                user.role = form.cleaned_data.get('role')  # fallback

            # ✅ Assign program from dropdown (students & lecturers both pick one)
            program = form.cleaned_data.get('program')
            if program:
                user.program = program

            user.save()
            login(request, user)
            return redirect_user_by_role(user)
    else:
        form = RegistrationForm()

    return render(request, 'UserLogin/register.html', {'form': form})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect_user_by_role(user)
    else:
        form = LoginForm()
    return render(request, 'UserLogin/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('landing')


# Helper function for role-based redirects
def redirect_user_by_role(user):
    if user.role == 'student':
        return redirect('student_dashboard')
    elif user.role == 'lecturer':
        return redirect('lecturer_dashboard')
    elif user.role == 'admin':
        return redirect('admin_dashboard')
    else:
        return redirect('login')


def landing_page(request):
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)
    return render(request, 'UserLogin/landing.html')
