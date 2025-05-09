# realistic_views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .realistic_blockchain import (
    BlockchainNode, SmartContract, Transaction, RealisticBlock, StudentRecord,
    BlockchainService, deploy_student_contract, add_student_via_contract,
    update_student_via_contract, invalidate_student_record, simulate_mining,
    get_student_data, get_student_history
)
from django.db import transaction
from cryptography.fernet import Fernet
import json
import base64
import hashlib
from django.http import JsonResponse

def is_admin(user):
    return user.is_superuser

@login_required(login_url='login')
@user_passes_test(is_admin)
def blockchain_explorer(request):
    """View blockchain explorer interface"""
    # Get blockchain stats
    is_valid, validation_message = BlockchainService.validate_blockchain()
    blocks = RealisticBlock.objects.all().order_by('-block_number')[:20]  # Latest 20 blocks
    pending_txs = Transaction.objects.filter(status=Transaction.PENDING).count()
    
    # Get contracts and nodes
    contracts = SmartContract.objects.all()
    nodes = BlockchainNode.objects.all()
    
    # Simulate a wallet address for the current user
    user_address = hashlib.sha256(f"user_{request.user.id}".encode()).hexdigest()
    
    context = {
        'is_valid': is_valid,
        'validation_message': validation_message,
        'blocks': blocks,
        'pending_transactions': pending_txs,
        'contracts': contracts,
        'nodes': nodes,
        'user_address': user_address
    }
    
    return render(request, 'blockchain_explorer.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin)
def block_detail(request, block_number):
    """View block details"""
    try:
        block = RealisticBlock.objects.get(block_number=block_number)
        transactions = block.transactions.all()
        
        context = {
            'block': block,
            'transactions': transactions
        }
        
        return render(request, 'block_detail.html', context)
    except RealisticBlock.DoesNotExist:
        messages.error(request, f"Block #{block_number} not found")
        return redirect('blockchain_explorer')

@login_required(login_url='login')
@user_passes_test(is_admin)
def transaction_detail(request, tx_hash):
    """View transaction details"""
    try:
        tx = Transaction.objects.get(transaction_hash=tx_hash)
        
        # Get additional info based on transaction type
        tx_data = None
        try:
            if tx.to_address and SmartContract.objects.filter(contract_address=tx.to_address).exists():
                # This is a contract call
                tx_data = json.loads(tx.data)
        except json.JSONDecodeError:
            pass
        
        context = {
            'transaction': tx,
            'tx_data': tx_data
        }
        
        return render(request, 'transaction_detail.html', context)
    except Transaction.DoesNotExist:
        messages.error(request, f"Transaction not found")
        return redirect('blockchain_explorer')

@login_required(login_url='login')
@user_passes_test(is_admin)
def student_blockchain_view(request):
    """View students on the blockchain"""
    # Get active student records
    active_records = StudentRecord.objects.filter(status='active')
    
    context = {
        'student_records': active_records
    }
    
    return render(request, 'realistic/student_blockchain_view.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin)
def student_record_detail(request, student_id):
    """View student record details"""
    # Get record history
    result = get_student_history(student_id)
    
    if not result.get('success', False):
        messages.error(request, result.get('error', 'Student not found'))
        return redirect('student_blockchain_view')
    
    context = {
        'student_id': student_id,
        'record_history': result.get('history', [])
    }
    
    return render(request, 'student_record_detail.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin)
def add_student_blockchain(request):
    """Add a student using blockchain smart contract"""
    # Deploy contract if not already deployed
    contract = deploy_student_contract(request.user)
    
    # Simulate a wallet address for the current user
    user_address = hashlib.sha256(f"user_{request.user.id}".encode()).hexdigest()
    
    if request.method == 'POST':
        # Get form data
        student_id = request.POST.get('nis')
        nisn = request.POST.get('nisn')
        nama = request.POST.get('nama')
        kelahiran = request.POST.get('kelahiran')
        kelamin = request.POST.get('kelamin')
        alamat = request.POST.get('alamat')
        
        # Create student data dictionary
        student_data = {
            'nisn': nisn,
            'nama': nama,
            'kelahiran': kelahiran,
            'kelamin': kelamin,
            'alamat': alamat
        }
        
        # Generate encryption key
        key = Fernet.generate_key()
        fernet = Fernet(key)
        
        # Encrypt data
        json_data = json.dumps(student_data)
        encrypted_data = fernet.encrypt(json_data.encode())
        
        # Submit transaction to contract
        tx, result = add_student_via_contract(
            user_address=user_address,
            contract_address=contract.contract_address,
            student_id=student_id,
            encrypted_data=encrypted_data
        )
        
        if result.get('success', False):
            # Mine block to include transaction
            mining_success, mining_message = simulate_mining(user_address)
            
            if mining_success:
                messages.success(request, f"Student {student_id} added to blockchain successfully and mined in a new block")
            else:
                messages.warning(request, f"Student {student_id} transaction created but mining failed: {mining_message}")
        else:
            messages.error(request, f"Failed to add student: {result.get('error', 'Unknown error')}")
        
        return redirect('student_blockchain_view')
    
    return render(request, 'realistic/add_student_blockchain.html', {
        'contract': contract,
        'user_address': user_address
    })

@login_required(login_url='login')
@user_passes_test(is_admin)
def update_student_blockchain(request, student_id):
    """Update a student using blockchain smart contract"""
    # Get the smart contract
    try:
        contract = SmartContract.objects.get(name="StudentManagement")
    except SmartContract.DoesNotExist:
        contract = deploy_student_contract(request.user)
    
    # Simulate a wallet address for the current user
    user_address = hashlib.sha256(f"user_{request.user.id}".encode()).hexdigest()
    
    # Get current student data
    student_result = get_student_data(student_id)
    
    if not student_result.get('success', False):
        messages.error(request, f"Student not found: {student_result.get('error', 'Unknown error')}")
        return redirect('student_blockchain_view')
    
    if request.method == 'POST':
        # Get form data
        nisn = request.POST.get('nisn')
        nama = request.POST.get('nama')
        kelahiran = request.POST.get('kelahiran')
        kelamin = request.POST.get('kelamin')
        alamat = request.POST.get('alamat')
        
        # Create student data dictionary
        student_data = {
            'nisn': nisn,
            'nama': nama,
            'kelahiran': kelahiran,
            'kelamin': kelamin,
            'alamat': alamat
        }
        
        # Generate encryption key
        key = Fernet.generate_key()
        fernet = Fernet(key)
        
        # Encrypt data
        json_data = json.dumps(student_data)
        encrypted_data = fernet.encrypt(json_data.encode())
        
        # Submit transaction to contract
        tx, result = update_student_via_contract(
            user_address=user_address,
            contract_address=contract.contract_address,
            student_id=student_id,
            encrypted_data=encrypted_data
        )
        
        if result.get('success', False):
            # Mine block to include transaction
            mining_success, mining_message = simulate_mining(user_address)
            
            if mining_success:
                messages.success(request, f"Student {student_id} updated in blockchain successfully and mined in a new block")
            else:
                messages.warning(request, f"Student {student_id} update transaction created but mining failed: {mining_message}")
        else:
            messages.error(request, f"Failed to update student: {result.get('error', 'Unknown error')}")
        
        return redirect('student_blockchain_view')
    
    # Get current data for form
    current_data = {
        'student_id': student_id,
        # In a real application, we would decrypt the data here
        # For this simulation, we'll use placeholder data
        'nisn': '123456789',
        'nama': 'Placeholder Name',
        'kelahiran': 'Placeholder Birth',
        'kelamin': 'LAKI-LAKI',
        'alamat': 'Placeholder Address'
    }
    
    return render(request, 'update_student_blockchain.html', {
        'contract': contract,
        'user_address': user_address,
        'student_id': student_id,
        'current_data': current_data
    })

@login_required(login_url='login')
@user_passes_test(is_admin)
def invalidate_student_blockchain(request, student_id):
    """Invalidate a student record using blockchain smart contract"""
    # Get the smart contract
    try:
        contract = SmartContract.objects.get(name="StudentManagement")
    except SmartContract.DoesNotExist:
        contract = deploy_student_contract(request.user)
    
    # Simulate a wallet address for the current user
    user_address = hashlib.sha256(f"user_{request.user.id}".encode()).hexdigest()
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided')
        
        # Submit transaction to contract
        tx, result = invalidate_student_record(
            user_address=user_address,
            contract_address=contract.contract_address,
            student_id=student_id,
            reason=reason
        )
        
        if result.get('success', False):
            # Mine block to include transaction
            mining_success, mining_message = simulate_mining(user_address)
            
            if mining_success:
                messages.success(request, f"Student {student_id} record invalidated successfully and mined in a new block")
            else:
                messages.warning(request, f"Student {student_id} invalidation transaction created but mining failed: {mining_message}")
        else:
            messages.error(request, f"Failed to invalidate student record: {result.get('error', 'Unknown error')}")
        
        return redirect('student_blockchain_view')
    
    return render(request, 'invalidate_student_blockchain.html', {
        'contract': contract,
        'user_address': user_address,
        'student_id': student_id
    })

@login_required(login_url='login')
@user_passes_test(is_admin)
def mine_pending_transactions(request):
    """Mine pending transactions into a new block"""
    if request.method == 'POST':
        # Simulate a wallet address for the current user
        user_address = hashlib.sha256(f"user_{request.user.id}".encode()).hexdigest()
        
        # Mine pending transactions
        success, message = simulate_mining(user_address)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, f"Mining failed: {message}")
        
        return redirect('blockchain_explorer')
    
    # GET request - show confirmation page
    pending_count = Transaction.objects.filter(status=Transaction.PENDING).count()
    
    return render(request, 'mine_transactions.html', {
        'pending_count': pending_count
    })

@login_required(login_url='login')
@user_passes_test(is_admin)
def setup_blockchain(request):
    """Initial blockchain setup"""
    if request.method == 'POST':
        # Create genesis block if not exists
        genesis = BlockchainService.create_genesis_block()
        
        # Create default node for current user
        node_address = hashlib.sha256(f"node_{request.user.id}".encode()).hexdigest()
        
        node, created = BlockchainNode.objects.get_or_create(
            address=node_address,
            defaults={
                'name': f"{request.user.username}'s Node",
                'is_validator': True,
                'public_key': "simulation_public_key"
            }
        )
        
        # Deploy student contract
        contract = deploy_student_contract(request.user)
        
        messages.success(request, f"Blockchain initialized with genesis block, node created, and student contract deployed at {contract.contract_address[:10]}...")
        return redirect('blockchain_explorer')
    
    # Check if blockchain is already set up
    has_genesis = RealisticBlock.objects.filter(block_number=0).exists()
    has_node = BlockchainNode.objects.exists()
    has_contract = SmartContract.objects.filter(name="StudentManagement").exists()
    
    context = {
        'has_genesis': has_genesis,
        'has_node': has_node,
        'has_contract': has_contract,
        'is_setup': has_genesis and has_node and has_contract
    }
    
    return render(request, 'setup_blockchain.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin)
def create_fix_transaction(request):
    """
    Create a transaction to fix an issue with a student record
    This demonstrates how real blockchains handle errors - with new transactions, not by modifying history
    """
    # Get the smart contract
    try:
        contract = SmartContract.objects.get(name="StudentManagement")
    except SmartContract.DoesNotExist:
        contract = deploy_student_contract(request.user)
    
    # Simulate a wallet address for the current user
    user_address = hashlib.sha256(f"user_{request.user.id}".encode()).hexdigest()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        student_id = request.POST.get('student_id')
        reason = request.POST.get('reason', '')
        
        if action == 'invalidate':
            # Invalidate incorrect record
            tx, result = invalidate_student_record(
                user_address=user_address,
                contract_address=contract.contract_address,
                student_id=student_id,
                reason=reason
            )
            
            if not result.get('success', False):
                messages.error(request, f"Failed to invalidate record: {result.get('error', 'Unknown error')}")
                return redirect('create_fix_transaction')
            
            # Mine the invalidation transaction
            mining_success, mining_message = simulate_mining(user_address)
            
            if not mining_success:
                messages.error(request, f"Failed to mine invalidation transaction: {mining_message}")
                return redirect('create_fix_transaction')
            
            messages.success(request, f"Successfully invalidated record for {student_id} with reason: {reason}")
            return redirect('student_blockchain_view')
            
        elif action == 'create_corrected':
            # Create a new, corrected record
            nisn = request.POST.get('nisn')
            nama = request.POST.get('nama')
            kelahiran = request.POST.get('kelahiran')
            kelamin = request.POST.get('kelamin')
            alamat = request.POST.get('alamat')
            
            # Create student data dictionary
            student_data = {
                'nisn': nisn,
                'nama': nama,
                'kelahiran': kelahiran,
                'kelamin': kelamin,
                'alamat': alamat,
                'correction_note': reason
            }
            
            # Generate encryption key
            key = Fernet.generate_key()
            fernet = Fernet(key)
            
            # Encrypt data
            json_data = json.dumps(student_data)
            encrypted_data = fernet.encrypt(json_data.encode())
            
            # Add the corrected record
            tx, result = add_student_via_contract(
                user_address=user_address,
                contract_address=contract.contract_address,
                student_id=student_id,
                encrypted_data=encrypted_data
            )
            
            if not result.get('success', False):
                messages.error(request, f"Failed to create corrected record: {result.get('error', 'Unknown error')}")
                return redirect('create_fix_transaction')
            
            # Mine the new record transaction
            mining_success, mining_message = simulate_mining(user_address)
            
            if not mining_success:
                messages.error(request, f"Failed to mine new record transaction: {mining_message}")
                return redirect('create_fix_transaction')
            
            messages.success(request, f"Successfully created corrected record for {student_id}")
            return redirect('student_blockchain_view')
    
    # Get all active student records for selection
    active_records = StudentRecord.objects.filter(status='active')
    
    context = {
        'contract': contract,
        'user_address': user_address,
        'active_records': active_records
    }
    
    return render(request, 'create_fix_transaction.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin)
def fix_block3_issue(request):
    """
    Special page to demonstrate how to handle the Block #3 issue in a realistic blockchain
    This uses corrective transactions rather than modifying history
    """
    # Check if we have the problematic setup (Block #3 pointing to Block #1)
    has_issue = False
    block3 = None
    block2 = None
    
    try:
        block3 = RealisticBlock.objects.get(block_number=3)
        block2 = RealisticBlock.objects.get(block_number=2)
        
        # Check if block3 is pointing to block1 instead of block2
        block1 = RealisticBlock.objects.get(block_number=1)
        if block3.previous_hash == block1.block_hash:
            has_issue = True
    except RealisticBlock.DoesNotExist:
        pass
    
    # Get the smart contract
    try:
        contract = SmartContract.objects.get(name="StudentManagement")
    except SmartContract.DoesNotExist:
        contract = deploy_student_contract(request.user)
    
    # Simulate a wallet address for the current user
    user_address = hashlib.sha256(f"user_{request.user.id}".encode()).hexdigest()
    
    if request.method == 'POST' and has_issue:
        # Step 1: Find student record in block 3
        try:
            # This is a simplification - in a real blockchain, we'd find this differently
            student_record = None
            for tx in block3.transactions.all():
                # Try to find a transaction that created a student record
                try:
                    tx_data = json.loads(tx.data)
                    if tx_data.get('function') == 'add_student':
                        # Get the student ID
                        params = tx_data.get('params', {})
                        student_id = params.get('student_id')
                        if student_id:
                            # Find the record
                            student_record = StudentRecord.objects.filter(
                                student_id=student_id, 
                                status='active'
                            ).first()
                            break
                except:
                    continue
            
            if not student_record:
                messages.error(request, "Could not find student record in Block #3")
                return redirect('blockchain_explorer')
            
            # Step 2: Create transaction to invalidate the record
            tx, result = invalidate_student_record(
                user_address=user_address,
                contract_address=contract.contract_address,
                student_id=student_record.student_id,
                reason="Record in Block #3 with invalid chain reference"
            )
            
            if not result.get('success', False):
                messages.error(request, f"Failed to invalidate record: {result.get('error', 'Unknown error')}")
                return redirect('fix_block3_issue')
            
            # Step 3: Mine the invalidation transaction
            mining_success, mining_message = simulate_mining(user_address)
            
            if not mining_success:
                messages.error(request, f"Failed to mine invalidation transaction: {mining_message}")
                return redirect('fix_block3_issue')
            
            # Step 4: Create a corrected record
            # Here we would normally decrypt the old data, but for simplicity we'll use placeholder data
            corrected_data = {
                'nisn': '123456789',
                'nama': f"Corrected {student_record.student_id}",
                'kelahiran': 'JAKARTA, 01 JANUARY 2000',
                'kelamin': 'LAKI-LAKI',
                'alamat': 'Corrected Address',
                'correction_note': "This record replaces an invalid record from Block #3"
            }
            
            # Generate encryption key
            key = Fernet.generate_key()
            fernet = Fernet(key)
            
            # Encrypt data
            json_data = json.dumps(corrected_data)
            encrypted_data = fernet.encrypt(json_data.encode())
            
            # Add the corrected record
            tx, result = add_student_via_contract(
                user_address=user_address,
                contract_address=contract.contract_address,
                student_id=student_record.student_id,
                encrypted_data=encrypted_data
            )
            
            if not result.get('success', False):
                messages.error(request, f"Failed to create corrected record: {result.get('error', 'Unknown error')}")
                return redirect('fix_block3_issue')
            
            # Step 5: Mine the new record transaction
            mining_success, mining_message = simulate_mining(user_address)
            
            if not mining_success:
                messages.error(request, f"Failed to mine new record transaction: {mining_message}")
                return redirect('fix_block3_issue')
            
            messages.success(request, 
                "Successfully fixed the Block #3 issue by:\n"
                "1. Invalidating the record in the invalid block\n"
                "2. Creating a new corrected record in a valid block\n"
                "Note: We cannot modify the blockchain history, so Block #3 remains invalid, "
                "but its data is now superseded by a valid record."
            )
            
            return redirect('blockchain_explorer')
            
        except Exception as e:
            messages.error(request, f"Error fixing Block #3 issue: {str(e)}")
            return redirect('blockchain_explorer')
    
    context = {
        'has_issue': has_issue,
        'block3': block3,
        'block2': block2,
        'contract': contract,
        'user_address': user_address
    }
    
    return render(request, 'fix_block3_issue.html', context)

# Add these views to urls.py:
"""

"""