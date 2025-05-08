# biodata/realistic_blockchain.py

from django.db import models, transaction
from django.contrib.auth.models import User
import hashlib
import json
from datetime import datetime
from cryptography.fernet import Fernet
import base64
from django.conf import settings
import time
import random

class BlockchainNode(models.Model):
    """Represents a node in the blockchain network"""
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=64, unique=True)
    is_validator = models.BooleanField(default=False)
    public_key = models.TextField()
    
    def __str__(self):
        return self.name

class SmartContract(models.Model):
    """Represents a deployed smart contract"""
    contract_address = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=20)
    bytecode = models.TextField()  # In a real system, this would be compiled bytecode
    abi = models.TextField()  # Contract interface in JSON format
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} v{self.version} ({self.contract_address[:10]}...)"

class Transaction(models.Model):
    """Represents a blockchain transaction"""
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (CONFIRMED, 'Confirmed'),
        (REJECTED, 'Rejected'),
    ]
    
    transaction_hash = models.CharField(max_length=64, unique=True)
    from_address = models.CharField(max_length=64)
    to_address = models.CharField(max_length=64)  # Contract address or recipient
    data = models.TextField()  # Function call data or transfer data
    signature = models.TextField()
    gas_used = models.IntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Tx: {self.transaction_hash[:10]}... ({self.status})"

class RealisticBlock(models.Model):
    """Represents a block in a realistic blockchain"""
    block_number = models.IntegerField(unique=True)
    block_hash = models.CharField(max_length=64, unique=True)
    previous_hash = models.CharField(max_length=64)
    timestamp = models.DateTimeField(auto_now_add=True)
    merkle_root = models.CharField(max_length=64)
    difficulty = models.IntegerField(default=2)  # Number of leading zeros required
    nonce = models.IntegerField(default=0)
    miner = models.ForeignKey(BlockchainNode, on_delete=models.SET_NULL, null=True)
    transactions = models.ManyToManyField(Transaction)
    
    def __str__(self):
        return f"Block #{self.block_number} ({self.block_hash[:10]}...)"
    
    class Meta:
        ordering = ['-block_number']

class StudentContract:
    """
    Smart contract for student records
    In a real blockchain, this would be deployed code, not a Python class
    """
    
    @staticmethod
    def add_student(transaction_data):
        """
        Add a new student record
        In a real smart contract, this would be a function anyone can call
        """
        try:
            # Parse function call data
            data = json.loads(transaction_data)
            student_id = data.get('student_id')
            encrypted_data = data.get('encrypted_data')
            
            # Validate input
            if not student_id or not encrypted_data:
                return {'success': False, 'error': 'Missing required parameters'}
            
            # Check if student already exists
            if StudentRecord.objects.filter(student_id=student_id).exists():
                return {'success': False, 'error': 'Student already exists'}
            
            # Create student record
            record = StudentRecord.objects.create(
                student_id=student_id,
                encrypted_data=encrypted_data,
                status='active'
            )
            
            # In a real smart contract, this would emit an event
            return {
                'success': True, 
                'student_id': student_id,
                'record_id': record.id
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def update_student(transaction_data):
        """Update existing student record"""
        try:
            # Parse function call data
            data = json.loads(transaction_data)
            student_id = data.get('student_id')
            encrypted_data = data.get('encrypted_data')
            
            # Validate input
            if not student_id or not encrypted_data:
                return {'success': False, 'error': 'Missing required parameters'}
            
            # Find student record
            try:
                record = StudentRecord.objects.get(student_id=student_id, status='active')
            except StudentRecord.DoesNotExist:
                return {'success': False, 'error': 'Student not found'}
            
            # Create a new version of the record
            new_record = StudentRecord.objects.create(
                student_id=student_id,
                encrypted_data=encrypted_data,
                previous_version=record,
                status='active'
            )
            
            # Mark previous record as superseded
            record.status = 'superseded'
            record.save()
            
            return {
                'success': True, 
                'student_id': student_id,
                'record_id': new_record.id,
                'previous_record_id': record.id
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_student(student_id):
        """Get the latest version of a student record"""
        try:
            record = StudentRecord.objects.get(student_id=student_id, status='active')
            return {
                'success': True,
                'student_id': record.student_id,
                'encrypted_data': record.encrypted_data,
                'record_id': record.id,
                'created_at': record.created_at
            }
        except StudentRecord.DoesNotExist:
            return {'success': False, 'error': 'Student not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_record_history(student_id):
        """Get all versions of a student record"""
        try:
            records = StudentRecord.objects.filter(student_id=student_id).order_by('-created_at')
            
            if not records:
                return {'success': False, 'error': 'Student not found'}
            
            history = []
            for record in records:
                history.append({
                    'record_id': record.id,
                    'status': record.status,
                    'created_at': record.created_at,
                    'encrypted_data': record.encrypted_data
                })
            
            return {
                'success': True,
                'student_id': student_id,
                'history': history
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def invalidate_record(transaction_data):
        """Mark a record as invalid (but doesn't delete it)"""
        try:
            # Parse function call data
            data = json.loads(transaction_data)
            student_id = data.get('student_id')
            reason = data.get('reason', 'No reason provided')
            
            # Validate input
            if not student_id:
                return {'success': False, 'error': 'Missing student_id parameter'}
            
            # Find student record
            try:
                record = StudentRecord.objects.get(student_id=student_id, status='active')
            except StudentRecord.DoesNotExist:
                return {'success': False, 'error': 'Active student record not found'}
            
            # Mark record as invalid
            record.status = 'invalid'
            record.notes = f"Invalidated: {reason}"
            record.save()
            
            return {
                'success': True, 
                'student_id': student_id,
                'record_id': record.id,
                'status': 'invalid'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

class StudentRecord(models.Model):
    """Model representing a student record in the blockchain"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('superseded', 'Superseded'),
        ('invalid', 'Invalid')
    ]
    
    student_id = models.CharField(max_length=20, db_index=True)  # NIS
    encrypted_data = models.BinaryField()  # Encrypted student data
    previous_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Student {self.student_id} ({self.status})"
    
    class Meta:
        indexes = [
            models.Index(fields=['student_id', 'status']),
        ]

class BlockchainService:
    """Service for interacting with the blockchain"""
    
    @staticmethod
    def create_genesis_block():
        """Create genesis block if not exists"""
        if RealisticBlock.objects.exists():
            return RealisticBlock.objects.order_by('block_number').first()
        
        # Create genesis block
        genesis_block = RealisticBlock(
            block_number=0,
            previous_hash="0" * 64,
            merkle_root=hashlib.sha256("genesis".encode()).hexdigest(),
            difficulty=2,
            nonce=0
        )
        
        # Calculate block hash
        block_data = (
            str(genesis_block.block_number) +
            str(genesis_block.previous_hash) +
            str(genesis_block.timestamp.timestamp()) +
            str(genesis_block.merkle_root) +
            str(genesis_block.nonce)
        )
        
        # Mine block (find valid nonce)
        while True:
            block_hash = hashlib.sha256(block_data.encode()).hexdigest()
            if block_hash.startswith("0" * genesis_block.difficulty):
                break
            genesis_block.nonce += 1
            block_data = block_data[:-len(str(genesis_block.nonce))] + str(genesis_block.nonce)
        
        genesis_block.block_hash = block_hash
        genesis_block.save()
        
        return genesis_block
    
    @staticmethod
    def create_transaction(from_address, to_address, data, private_key=None):
        """Create a new transaction"""
        # In a real system, this would be signed with the private key
        transaction_data = {
            'from': from_address,
            'to': to_address,
            'data': data,
            'timestamp': datetime.now().timestamp()
        }
        
        # Create transaction hash
        tx_string = json.dumps(transaction_data, sort_keys=True)
        tx_hash = hashlib.sha256(tx_string.encode()).hexdigest()
        
        # In a real system, create a signature using the private key
        signature = "simulated_signature"  # Placeholder
        
        # Create transaction
        transaction = Transaction.objects.create(
            transaction_hash=tx_hash,
            from_address=from_address,
            to_address=to_address,
            data=data,
            signature=signature,
            status=Transaction.PENDING
        )
        
        return transaction
    
    @staticmethod
    def process_transaction(transaction):
        """
        Process a transaction
        In a real blockchain, this would be done by validator nodes
        """
        # Validate transaction
        # In a real system, verify signature, check balance, etc.
        
        # Determine if this is a contract call
        try:
            contract = SmartContract.objects.get(contract_address=transaction.to_address)
            
            # Call the appropriate contract function
            # In a real system, this would execute bytecode in a VM
            # Here we're simulating by calling Python functions
            
            # Parse the function call (in a real system this would be ABI-encoded)
            try:
                call_data = json.loads(transaction.data)
                function_name = call_data.get('function')
                function_data = json.dumps(call_data.get('params', {}))
                
                if function_name == 'add_student':
                    result = StudentContract.add_student(function_data)
                elif function_name == 'update_student':
                    result = StudentContract.update_student(function_data)
                elif function_name == 'invalidate_record':
                    result = StudentContract.invalidate_record(function_data)
                else:
                    result = {'success': False, 'error': f'Unknown function: {function_name}'}
                
                # Update transaction status based on result
                if result.get('success', False):
                    transaction.status = Transaction.CONFIRMED
                else:
                    transaction.status = Transaction.REJECTED
                
                # Set gas used (in a real system this would be calculated)
                transaction.gas_used = random.randint(50000, 100000)
                transaction.save()
                
                return result
                
            except json.JSONDecodeError:
                transaction.status = Transaction.REJECTED
                transaction.save()
                return {'success': False, 'error': 'Invalid function call data'}
                
        except SmartContract.DoesNotExist:
            # Not a contract call - could be a transfer or other transaction
            # For this simulation, we'll just mark it as confirmed
            transaction.status = Transaction.CONFIRMED
            transaction.save()
            return {'success': True}
    
    @staticmethod
    def mine_new_block(miner_address):
        """
        Mine a new block with pending transactions
        In a real blockchain, this would be done by miners/validators in a competitive process
        """
        # Get pending transactions
        pending_txs = Transaction.objects.filter(status=Transaction.PENDING)
        
        if not pending_txs:
            return None, "No pending transactions to mine"
        
        # Get latest block
        try:
            latest_block = RealisticBlock.objects.order_by('-block_number').first()
            if not latest_block:
                latest_block = BlockchainService.create_genesis_block()
        except RealisticBlock.DoesNotExist:
            latest_block = BlockchainService.create_genesis_block()
        
        # Create new block
        new_block = RealisticBlock(
            block_number=latest_block.block_number + 1,
            previous_hash=latest_block.block_hash,
            difficulty=latest_block.difficulty,  # In real systems, difficulty adjusts dynamically
            nonce=0
        )
        
        # Calculate merkle root of transactions
        tx_hashes = [tx.transaction_hash for tx in pending_txs]
        merkle_root = BlockchainService.calculate_merkle_root(tx_hashes)
        new_block.merkle_root = merkle_root
        
        # Find miner node
        try:
            miner = BlockchainNode.objects.get(address=miner_address)
            new_block.miner = miner
        except BlockchainNode.DoesNotExist:
            pass
        
        # Mine block (find valid nonce)
        block_data = (
            str(new_block.block_number) +
            str(new_block.previous_hash) +
            str(new_block.timestamp.timestamp()) +
            str(new_block.merkle_root) +
            str(new_block.nonce)
        )
        
        start_time = time.time()
        
        while True:
            block_hash = hashlib.sha256(block_data.encode()).hexdigest()
            if block_hash.startswith("0" * new_block.difficulty):
                break
            new_block.nonce += 1
            block_data = block_data[:-len(str(new_block.nonce))] + str(new_block.nonce)
            
            # Check if mining is taking too long (for simulation purposes)
            if time.time() - start_time > 10:  # Timeout after 10 seconds
                return None, "Mining timeout - adjust difficulty"
        
        new_block.block_hash = block_hash
        
        # Save the block and add transactions
        with transaction.atomic():
            new_block.save()
            new_block.transactions.set(pending_txs)
            
            # Update transaction status
            for tx in pending_txs:
                tx.status = Transaction.CONFIRMED
                tx.save()
        
        return new_block, "Block successfully mined"
    
    @staticmethod
    def calculate_merkle_root(hashes):
        """Calculate the Merkle root of a list of hashes"""
        if not hashes:
            return hashlib.sha256("empty".encode()).hexdigest()
        
        if len(hashes) == 1:
            return hashes[0]
        
        # Ensure even number of hashes
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])
        
        # Pair hashes and hash them together
        next_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i+1]
            next_hash = hashlib.sha256(combined.encode()).hexdigest()
            next_level.append(next_hash)
        
        # Recursively calculate until we have one hash
        return BlockchainService.calculate_merkle_root(next_level)
    
    @staticmethod
    def validate_blockchain():
        """Validate the integrity of the blockchain"""
        blocks = RealisticBlock.objects.all().order_by('block_number')
        
        if not blocks:
            return True, "Blockchain is empty"
        
        for i, block in enumerate(blocks):
            # Skip genesis block validation of previous hash
            if i == 0:
                if block.previous_hash != "0" * 64:
                    return False, f"Invalid genesis block: previous hash should be all zeros"
                continue
            
            # Validate previous hash points to previous block
            prev_block = blocks[i-1]
            if block.previous_hash != prev_block.block_hash:
                return False, f"Block #{block.block_number} has invalid previous_hash"
            
            # Validate block hash
            block_data = (
                str(block.block_number) +
                str(block.previous_hash) +
                str(block.timestamp.timestamp()) +
                str(block.merkle_root) +
                str(block.nonce)
            )
            calculated_hash = hashlib.sha256(block_data.encode()).hexdigest()
            
            if calculated_hash != block.block_hash:
                return False, f"Block #{block.block_number} has invalid block_hash"
            
            # Validate proof of work
            if not block.block_hash.startswith("0" * block.difficulty):
                return False, f"Block #{block.block_number} has invalid proof of work"
        
        return True, "Blockchain is valid"

# Smart Contract interaction functions
def deploy_student_contract(creator):
    """Deploy the student management contract"""
    # Check if contract already deployed
    if SmartContract.objects.filter(name="StudentManagement").exists():
        return SmartContract.objects.get(name="StudentManagement")
    
    # Generate a contract address
    contract_address = hashlib.sha256(f"StudentManagement{datetime.now().timestamp()}".encode()).hexdigest()
    
    # The ABI (Application Binary Interface) defines the contract's interface
    abi = json.dumps([
        {
            "name": "add_student",
            "inputs": [
                {"name": "student_id", "type": "string"},
                {"name": "encrypted_data", "type": "bytes"}
            ],
            "outputs": [
                {"name": "success", "type": "bool"},
                {"name": "student_id", "type": "string"},
                {"name": "record_id", "type": "uint256"}
            ]
        },
        {
            "name": "update_student",
            "inputs": [
                {"name": "student_id", "type": "string"},
                {"name": "encrypted_data", "type": "bytes"}
            ],
            "outputs": [
                {"name": "success", "type": "bool"},
                {"name": "student_id", "type": "string"},
                {"name": "record_id", "type": "uint256"},
                {"name": "previous_record_id", "type": "uint256"}
            ]
        },
        {
            "name": "invalidate_record",
            "inputs": [
                {"name": "student_id", "type": "string"},
                {"name": "reason", "type": "string"}
            ],
            "outputs": [
                {"name": "success", "type": "bool"},
                {"name": "student_id", "type": "string"},
                {"name": "record_id", "type": "uint256"},
                {"name": "status", "type": "string"}
            ]
        }
    ])
    
    # In a real system, this would be compiled bytecode
    # For our simulation, we'll use a placeholder
    bytecode = "0x608060405234801561001057600080fd5b50610828806100206000396000f3fe608060405234801561001057..."
    
    # Create the contract
    contract = SmartContract.objects.create(
        contract_address=contract_address,
        name="StudentManagement",
        version="1.0.0",
        bytecode=bytecode,
        abi=abi,
        creator=creator
    )
    
    return contract

def add_student_via_contract(user_address, contract_address, student_id, encrypted_data):
    """Add a student through the smart contract"""
    # Prepare transaction data
    call_data = {
        "function": "add_student",
        "params": {
            "student_id": student_id,
            "encrypted_data": base64.b64encode(encrypted_data).decode('utf-8')
        }
    }
    
    # Create transaction
    tx = BlockchainService.create_transaction(
        from_address=user_address,
        to_address=contract_address,
        data=json.dumps(call_data)
    )
    
    # Process transaction (in a real blockchain, this would happen through mining)
    result = BlockchainService.process_transaction(tx)
    
    return tx, result

def update_student_via_contract(user_address, contract_address, student_id, encrypted_data):
    """Update a student through the smart contract"""
    # Prepare transaction data
    call_data = {
        "function": "update_student",
        "params": {
            "student_id": student_id,
            "encrypted_data": base64.b64encode(encrypted_data).decode('utf-8')
        }
    }
    
    # Create transaction
    tx = BlockchainService.create_transaction(
        from_address=user_address,
        to_address=contract_address,
        data=json.dumps(call_data)
    )
    
    # Process transaction
    result = BlockchainService.process_transaction(tx)
    
    return tx, result

def invalidate_student_record(user_address, contract_address, student_id, reason):
    """Invalidate a student record through the smart contract"""
    # Prepare transaction data
    call_data = {
        "function": "invalidate_record",
        "params": {
            "student_id": student_id,
            "reason": reason
        }
    }
    
    # Create transaction
    tx = BlockchainService.create_transaction(
        from_address=user_address,
        to_address=contract_address,
        data=json.dumps(call_data)
    )
    
    # Process transaction
    result = BlockchainService.process_transaction(tx)
    
    return tx, result

def get_student_data(student_id):
    """Get student data (this doesn't require a transaction)"""
    return StudentContract.get_student(student_id)

def get_student_history(student_id):
    """Get student record history (doesn't require a transaction)"""
    return StudentContract.get_record_history(student_id)

def simulate_mining(user_address):
    """Simulate the mining process to add transactions to blockchain"""
    # In a real blockchain, mining is a competitive process
    # For our simulation, we'll just mine a block directly
    new_block, message = BlockchainService.mine_new_block(user_address)
    
    if new_block:
        return True, f"Block #{new_block.block_number} mined successfully with {new_block.transactions.count()} transactions"
    else:
        return False, message