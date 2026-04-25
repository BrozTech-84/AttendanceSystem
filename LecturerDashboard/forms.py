from django import forms
from StudentScanner.models import Course, Program

class CourseForm(forms.ModelForm):
    programs = forms.ModelMultipleChoiceField(
        queryset=Program.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Link Course to Program(s)"
    )

    class Meta:
        model = Course
        fields = ['name', 'code', 'programs']
