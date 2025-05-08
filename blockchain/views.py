# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from .models import StudentBiodata, Block, EncryptionKey
from .forms import StudentBiodataForm
from .services import BlockchainService
from django.db.models import F
from .repair import repair_blockchain
from .advanced_repair import repair_missing_blocks, detect_missing_blocks

# Helper function to check if user is admin
def is_admin(user):
    return user.is_superuser

@login_required(login_url='login')
@user_passes_test(is_admin)
def dashboard(request):
    """Admin dashboard showing blockchain statistics and block history"""
    stats = BlockchainService.get_blockchain_stats()
    is_valid, message = BlockchainService.validate_blockchain()
    
    # Get all blocks with their associated student data for the blockchain visualizer
    blocks = Block.objects.all().order_by('-id')  # Newest first
    
    # Try to add student data to each block and decrypt if possible
    try:
        key_obj = EncryptionKey.objects.get(user=request.user)
        
        for block in blocks:
            try:
                student = StudentBiodata.objects.get(block=block)
                block.student = student
                
                # Try to decrypt a preview of the data
                try:
                    decrypted_data = StudentBiodata.decrypt_data(student.encrypted_data, key_obj)
                    # Create a preview showing just the name
                    if decrypted_data.get('nama'):
                        block.student.decrypted_data = decrypted_data.get('nama')
                    else:
                        block.student.decrypted_data = None
                except Exception:
                    block.student.decrypted_data = None
                    
            except StudentBiodata.DoesNotExist:
                block.student = None
    except EncryptionKey.DoesNotExist:
        # If no encryption key, just mark all data as encrypted
        for block in blocks:
            try:
                block.student = StudentBiodata.objects.get(block=block)
                block.student.decrypted_data = None
            except StudentBiodata.DoesNotExist:
                block.student = None
    
    context = {
        'stats': stats,
        'blockchain_valid': is_valid,
        'validation_message': message,
        'blockchain_blocks': blocks,
    }
    return render(request, 'dashboard.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin)
def student_list(request):
    """List all students in the blockchain"""
    students = StudentBiodata.objects.all().order_by('-created_at')
    
    # Try to decrypt NISN and name for display in the list
    try:
        key_obj = EncryptionKey.objects.get(user=request.user)
        
        # Add decrypted data to each student object for display
        for student in students:
            try:
                decrypted_data = StudentBiodata.decrypt_data(student.encrypted_data, key_obj)
                student.decrypted_nisn = decrypted_data.get('nisn', '')
                student.decrypted_nama = decrypted_data.get('nama', '')
            except Exception:
                # If decryption fails, leave as None
                student.decrypted_nisn = None
                student.decrypted_nama = None
    except EncryptionKey.DoesNotExist:
        # If no key, mark all as encrypted
        for student in students:
            student.decrypted_nisn = None
            student.decrypted_nama = None
    
    paginator = Paginator(students, 10)  # Show 10 students per page
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'student_list.html', {'page_obj': page_obj})

@login_required(login_url='login')
@user_passes_test(is_admin)
def add_student(request):
    """Add a new student to the blockchain"""
    if request.method == 'POST':
        form = StudentBiodataForm(request.POST)
        if form.is_valid():
            # Get the validated data
            student_data = form.get_data_dict()
            
            # Extract NIS to use as student_id (the primary identifier)
            student_id = student_data.pop('nis')  # Changed from student_id to nis
            
            # Create a new student record in the blockchain
            try:
                StudentBiodata.create_with_blockchain(
                    student_id=student_id,  # This remains as student_id in the function parameter
                    data=student_data,
                    user=request.user
                )
                messages.success(request, f"Siswa dengan NIS {student_id} berhasil ditambahkan ke blockchain")
                return redirect('student_list')
            except Exception as e:
                messages.error(request, f"Error menambahkan siswa ke blockchain: {str(e)}")
    else:
        form = StudentBiodataForm()
    
    return render(request, 'add_student.html', {'form': form})


@login_required(login_url='login')
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
        return render(request, 'view_student.html', context)
    except EncryptionKey.DoesNotExist:
        messages.error(request, "Encryption key not found for your account")
    except Exception as e:
        messages.error(request, f"Error decrypting data: {str(e)}")
    
    return redirect('student_list')

@login_required(login_url='login')
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
                new_student_id = student_data.pop('nis')  # Changed from student_id to nis
                
                # Ensure NIS hasn't changed
                if new_student_id != student_id:
                    messages.error(request, "NIS tidak dapat diubah")
                    return redirect('update_student', student_id=student_id)
                
                # Update the student record
                student.update_data(student_data, request.user)
                messages.success(request, f"Data siswa dengan NIS {student_id} berhasil diperbarui")
                return redirect('student_list')
        else:
            # Pre-populate the form with current data
            initial_data = current_data.copy()
            initial_data['nis'] = student_id  # Changed from student_id to nis
            form = StudentBiodataForm(initial=initial_data)
        
        return render(request, 'update_student.html', {'form': form, 'student_id': student_id})
    
    except EncryptionKey.DoesNotExist:
        messages.error(request, "Kunci enkripsi tidak ditemukan untuk akun Anda")
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
    
    return redirect('student_list')

@login_required(login_url='login')
@user_passes_test(is_admin)
def validate_blockchain(request):
    """Validate the blockchain and return results as JSON"""
    is_valid, message = BlockchainService.validate_blockchain()
    return JsonResponse({'valid': is_valid, 'message': message})

@login_required(login_url='login')
@user_passes_test(is_admin)
def generate_key(request):
    """Generate a new encryption key for the admin"""
    if request.method == 'POST':
        # This will create a new key and invalidate any previously encrypted data
        EncryptionKey.generate_key(request.user)
        messages.success(request, "New encryption key generated successfully")
        return redirect('dashboard')
    
    return render(request, 'generate_key.html')


@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def repair_blockchain_view(request):
    """Repair blockchain integrity issues"""
    if request.method == 'POST':
        success, message, fixed_blocks = repair_blockchain()
        
        if success:
            messages.success(request, message)
        else:
            messages.warning(request, message)
            
        return redirect('dashboard')
    
    # GET request shows confirmation page
    is_valid, validation_message = BlockchainService.validate_blockchain()
    
    return render(request, 'repair_blockchain.html', {
        'is_valid': is_valid,
        'validation_message': validation_message
    })

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def advanced_repair_view(request):
    """Advanced repair for missing blocks"""
    # Detect missing blocks first
    missing_ids = detect_missing_blocks()
    
    if request.method == 'POST':
        success, message, fixed_blocks = repair_missing_blocks()
        
        if success:
            messages.success(request, message)
        else:
            messages.warning(request, message)
            
        return redirect('dashboard')
    
    # Get chain validation status
    is_valid, validation_message = BlockchainService.validate_blockchain()
    
    return render(request, 'advanced_repair.html', {
        'is_valid': is_valid,
        'validation_message': validation_message,
        'missing_ids': missing_ids
    })

