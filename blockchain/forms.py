from django import forms
import re

class StudentBiodataForm(forms.Form):
    """Form for validating student biodata in Indonesian format"""
    nis = forms.CharField(max_length=20, label="NIS")
    nisn = forms.CharField(max_length=20, label="NISN")
    nama = forms.CharField(max_length=255, label="Nama Lengkap")
    kelahiran = forms.CharField(max_length=100, label="Tempat, Tanggal Lahir")
    kelamin = forms.ChoiceField(
        choices=[('LAKI-LAKI', 'Laki-laki'), ('PEREMPUAN', 'Perempuan')],
        label="Jenis Kelamin"
    )
    alamat = forms.CharField(widget=forms.Textarea, label="Alamat Lengkap")
    
    def clean_nis(self):
        """Validate the NIS format"""
        nis = self.cleaned_data.get('nis')
        # Example validation for NIS in format XX.XX.XX.XXX
        if not re.match(r'^\d{2}\.\d{2}\.\d{2}\.\d{3}$', nis):
            raise forms.ValidationError("NIS harus dalam format XX.XX.XX.XXX (contoh: 23.24.10.003)")
        return nis
    
    def clean_nisn(self):
        """Validate the NISN format"""
        nisn = self.cleaned_data.get('nisn')
        # NISN should be numeric and 10 digits
        if not nisn.isdigit() or len(nisn) != 9:
            raise forms.ValidationError("NISN harus berupa 9 digit angka")
        return nisn
    
    def clean_kelahiran(self):
        """Validate birth information format"""
        kelahiran = self.cleaned_data.get('kelahiran')
        # Just basic validation to ensure it contains a comma and a date
        if ',' not in kelahiran or not any(char.isdigit() for char in kelahiran):
            raise forms.ValidationError("Format kelahiran: KOTA, DD BULAN YYYY (contoh: BUTON, 20 NOVEMBER 2007)")
        return kelahiran
    
    def get_data_dict(self):
        """Return a dictionary of the validated data"""
        return self.cleaned_data