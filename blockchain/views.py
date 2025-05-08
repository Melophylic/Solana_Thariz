# biodata/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from .models import StudentBiodata, Block, EncryptionKey
from .forms import StudentBiodataForm
from .services import BlockchainService

# Helper function to check if user is admin
def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """Admin dashboard showing blockchain statistics"""
    stats = BlockchainService.get_blockchain_stats()
    is_valid, message = BlockchainService.validate_blockchain()
    
    context = {
        'stats': stats,
        'blockchain_valid': is_valid,
        'validation_message': message,
    }
    return render(request, 'biodata/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def student_list(request):
    """List all students in the blockchain"""
    students = StudentBiodata.objects.all().order_by('-created_at')
    paginator = Paginator(students, 10)  # Show 10 students per page
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'biodata/student_list.html', {'page_obj': page_obj})

@login_required
@user_passes_test(is_admin)
def add_student(request):
    """Add a new student to the blockchain"""
    if request.method == 'POST':
        form = StudentBiodataForm(request.POST)
        if form.is_valid():
            # Get the validated data
            student_data = form.get_data_dict()
            student_id = student_data.pop('student_id')
            
            # Create a new student record in the blockchain
            try:
                StudentBiodata.create_with_blockchain(
                    student_id=student_id,
                    data=student_data,
                    user=request.user
                )
                messages.success(request, f"Student {student_id} added successfully to the blockchain")
                return redirect('student_list')
            except Exception as e:
                messages.error(request, f"Error adding student to blockchain: {str(e)}")
    else:
        form = StudentBiodataForm()
    
    return render(request, 'biodata/add_student.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def view_student(request, student_id):
    """View a student's decrypted data"""
    student = get_object_or_404(StudentBiodata, student_id=student_id)
    
    try:
        # Get the encryption key for the current user
        key_obj = EncryptionKey.objects.get(user=request.user)
        # Decrypt the data
        decrypted_data = StudentBiodata.decrypt_data(student.encrypted_data, key_obj)
        # Get block details
        block_details = BlockchainService.get_block_details(student.block.id)
        
        context = {
            'student': student,
            'student_data': decrypted_data,
            'block': block_details,
        }
        return render(request, 'biodata/view_student.html', context)
    except EncryptionKey.DoesNotExist:
        messages.error(request, "Encryption key not found for your account")
    except Exception as e:
        messages.error(request, f"Error decrypting data: {str(e)}")
    
    return redirect('student_list')

@login_required
@user_passes_test(is_admin)
def update_student(request, student_id):
    """Update a student's data"""
    student = get_object_or_404(StudentBiodata, student_id=student_id)
    
    try:
        # Get the encryption key for the current user
        key_obj = EncryptionKey.objects.get(user=request.user)
        # Get the current data
        current_data = StudentBiodata.decrypt_data(student.encrypted_data, key_obj)
        
        if request.method == 'POST':
            form = StudentBiodataForm(request.POST)
            if form.is_valid():
                # Get the validated data
                student_data = form.get_data_dict()
                new_student_id = student_data.pop('student_id')
                
                # Ensure student ID hasn't changed
                if new_student_id != student_id:
                    messages.error(request, "Student ID cannot be changed")
                    return redirect('update_student', student_id=student_id)
                
                # Update the student record
                student.update_data(student_data, request.user)
                messages.success(request, f"Student {student_id} updated successfully")
                return redirect('student_list')
        else:
            # Pre-populate the form with current data
            initial_data = current_data.copy()
            initial_data['student_id'] = student_id
            form = StudentBiodataForm(initial=initial_data)
        
        return render(request, 'biodata/update_student.html', {'form': form, 'student_id': student_id})
    
    except EncryptionKey.DoesNotExist:
        messages.error(request, "Encryption key not found for your account")
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
    
    return redirect('student_list')

@login_required
@user_passes_test(is_admin)
def validate_blockchain(request):
    """Validate the blockchain and return results as JSON"""
    is_valid, message = BlockchainService.validate_blockchain()
    return JsonResponse({'valid': is_valid, 'message': message})

@login_required
@user_passes_test(is_admin)
def generate_key(request):
    """Generate a new encryption key for the admin"""
    if request.method == 'POST':
        # This will create a new key and invalidate any previously encrypted data
        EncryptionKey.generate_key(request.user)
        messages.success(request, "New encryption key generated successfully")
        return redirect('dashboard')
    
    return render(request, 'biodata/generate_key.html')