# biodata/forms.py
from django import forms
import re

class StudentBiodataForm(forms.Form):
    """Form for validating student biodata"""
    student_id = forms.CharField(max_length=20)
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    phone_number = forms.CharField(max_length=15, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    department = forms.CharField(max_length=100, required=False)
    
    def clean_student_id(self):
        """Validate the student ID format"""
        student_id = self.cleaned_data.get('student_id')
        # Assuming student ID is in format ABC123 (3 letters followed by 3 digits)
        if not re.match(r'^[A-Z]{3}\d{3}$', student_id):
            raise forms.ValidationError("Student ID must be in format ABC123 (3 uppercase letters followed by 3 digits)")
        return student_id
    
    def clean_phone_number(self):
        """Validate phone number format"""
        phone = self.cleaned_data.get('phone_number')
        if phone and not re.match(r'^\+?[\d\s-]{10,15}$', phone):
            raise forms.ValidationError("Enter a valid phone number")
        return phone
    
    def clean(self):
        """Additional validation that requires multiple fields"""
        cleaned_data = super().clean()
        # Example: Ensure student is at least 16 years old
        dob = cleaned_data.get('date_of_birth')
        if dob:
            from datetime import date
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 16:
                self.add_error('date_of_birth', "Student must be at least 16 years old")
        
        return cleaned_data
    
    def get_data_dict(self):
        """Return a dictionary of the validated data"""
        return self.cleaned_data