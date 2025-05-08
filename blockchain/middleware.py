from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve

class AdminOnlyMiddleware:
    """
    Middleware to ensure only admin users can access the biodata app
    This provides an additional layer of security beyond view-level restrictions
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if request.path.startswith('/biodata/'):
            # Check if user is logged in and is an admin
            if not request.user.is_authenticated:
                return redirect('admin:login')
            
            if not request.user.is_superuser:
                messages.error(request, "Only administrators can access this area")
                return redirect('admin:login')
        
        # Continue processing the request
        response = self.get_response(request)
        return response