from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from .models import Program

User = get_user_model()

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    # Students pick ONE program, lecturers can pick MULTIPLE
    program = forms.ModelChoiceField(
        queryset=Program.objects.all(),
        required=False,
        empty_label="Select Program"
    )
    programs = forms.ModelMultipleChoiceField(
        queryset=Program.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Select Programs (Lecturer)"
    )

    role = forms.ChoiceField(
        choices=[('student', 'Student'), ('lecturer', 'Lecturer')],
        required=True
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'program', 'programs', 'role', 'password1', 'password2']

    def save(self, commit=True):   # ✅ must be inside the class
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']

        if user.role == 'student':
            user.program = self.cleaned_data['program']
        elif user.role == 'lecturer':
            user.save()  # must save before setting M2M
            user.programs.set(self.cleaned_data['programs'])

        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'})
    )
