# auth_views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.conf import settings
from django.utils.crypto import get_random_string
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django import forms  # Added this import which was missing
from .models import InvitationCode, EncryptionKey

class AdminRegistrationForm(UserCreationForm):
    """Form for creating administrator accounts"""
    invite_code = forms.CharField(max_length=20, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def clean_invite_code(self):
        """Validate the invitation code"""
        code = self.cleaned_data.get('invite_code')
        try:
            invite = InvitationCode.objects.get(code=code, is_used=False)
            return code
        except InvitationCode.DoesNotExist:
            raise forms.ValidationError("Invalid or expired invitation code")

def login_view(request):
    """Custom login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', 'dashboard')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active and user.is_staff:
                login(request, user)
                # Redirect to the specified URL or dashboard
                return redirect(next_url)
            else:
                messages.error(request, "Account is inactive or lacks administrator privileges")
        else:
            messages.error(request, "Invalid username or password")
    
    next_url = request.GET.get('next', '')
    return render(request, 'login.html', {'next': next_url})

def register_view(request):
    """View for admin registration"""
    if request.method == 'POST':
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            # Create user but mark as inactive until approved by superuser
            user = form.save(commit=False)
            user.is_active = False
            user.is_staff = True  # Staff status for admin panel access
            user.save()
            
            # Mark invitation code as used
            invite_code = form.cleaned_data.get('invite_code')
            invitation = InvitationCode.objects.get(code=invite_code)
            invitation.is_used = True
            invitation.used_by = user
            invitation.save()
            
            messages.success(request, "Registration successful! Your account will be activated after review by a superuser.")
            return redirect('login')
    else:
        form = AdminRegistrationForm()
    
    return render(request, 'admin_register.html', {'form': form})

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def generate_invitation(request):
    """Generate invitation codes for new administrators"""
    if request.method == 'POST':
        # Generate a random 10-character invitation code
        code = get_random_string(10).upper()
        
        # Create the invitation
        invitation = InvitationCode.objects.create(
            code=code,
            created_by=request.user,
            is_used=False
        )
        
        messages.success(request, f"Invitation code generated: {code}")
        return redirect('admin_invitations')
    
    return render(request, 'generate_invitation.html')

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def admin_invitations(request):
    """View and manage invitation codes"""
    invitations = InvitationCode.objects.all().order_by('-created_at')
    
    context = {
        'invitations': invitations
    }
    return render(request, 'admin_invitations.html', context)

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def admin_approval(request):
    """Approve or reject pending administrator accounts"""
    pending_users = User.objects.filter(is_active=False, is_staff=True)
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        if user_id and action:
            try:
                user = User.objects.get(id=user_id)
                
                if action == 'approve':
                    user.is_active = True
                    user.save()
                    
                    # Generate encryption key for the new admin
                    EncryptionKey.generate_key(user)
                    
                    messages.success(request, f"Administrator account for {user.username} has been approved and activated")
                elif action == 'reject':
                    # Consider whether to delete the user or just maintain the inactive status
                    user.delete()
                    messages.success(request, f"Administrator account for {user.username} has been rejected and removed")
            except User.DoesNotExist:
                messages.error(request, "User not found")
        
        return redirect('admin_approval')
    
    context = {
        'pending_users': pending_users
    }
    return render(request, 'admin_approval.html', context)