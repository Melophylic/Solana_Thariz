# biodata/models.py
import hashlib
import json
from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from cryptography.fernet import Fernet
import base64

class Block(models.Model):
    """Represents a block in our simplified blockchain"""
    previous_hash = models.CharField(max_length=64)
    timestamp = models.DateTimeField(auto_now_add=True)
    nonce = models.IntegerField(default=0)
    hash = models.CharField(max_length=64)
    
    def __str__(self):
        return f"Block {self.id} - {self.hash[:10]}..."

class EncryptionKey(models.Model):
    """Stores the encryption key for the admin"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    key = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    @classmethod
    def generate_key(cls, user):
        """Generate a new encryption key for a user"""
        key = Fernet.generate_key()
        key_obj, created = cls.objects.get_or_create(
            user=user,
            defaults={'key': key}
        )
        if not created:
            key_obj.key = key
            key_obj.save()
        return key_obj

class StudentBiodata(models.Model):
    """Model to store encrypted student biodata"""
    # Reference to the block in our blockchain
    block = models.OneToOneField(Block, on_delete=models.CASCADE)
    # Student ID - will be stored in plaintext for reference
    student_id = models.CharField(max_length=20, unique=True)
    # Encrypted data fields
    encrypted_data = models.BinaryField()
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Biodata for {self.student_id}"
    
    @staticmethod
    def encrypt_data(data, key_obj):
        """Encrypt the student data"""
        fernet = Fernet(key_obj.key)
        json_data = json.dumps(data)
        return fernet.encrypt(json_data.encode())
    
    @staticmethod
    def decrypt_data(encrypted_data, key_obj):
        """Decrypt the student data"""
        fernet = Fernet(key_obj.key)
        decrypted_data = fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())
    
    @staticmethod
    def calculate_hash(index, previous_hash, timestamp, data, nonce=0):
        """Calculate a SHA-256 hash of the block contents"""
        value = str(index) + str(previous_hash) + str(timestamp) + str(data) + str(nonce)
        return hashlib.sha256(value.encode()).hexdigest()
    
    @classmethod
    def create_with_blockchain(cls, student_id, data, user):
        """Create a new student record with blockchain integration"""
        # Get user's encryption key
        try:
            key_obj = EncryptionKey.objects.get(user=user)
        except EncryptionKey.DoesNotExist:
            key_obj = EncryptionKey.generate_key(user)
        
        # Encrypt the data
        encrypted_data = cls.encrypt_data(data, key_obj)
        
        # Get the previous block or create the genesis block
        try:
            previous_block = Block.objects.latest('id')
            previous_hash = previous_block.hash
            index = previous_block.id + 1
        except Block.DoesNotExist:
            previous_hash = "0" * 64  # Genesis block
            index = 0
        
        # Create a new block
        timestamp = datetime.now().timestamp()
        nonce = 0
        hash_value = cls.calculate_hash(index, previous_hash, timestamp, encrypted_data, nonce)
        
        # Simple PoW simulation - not actual mining
        while not hash_value.startswith('00'):  # Simple difficulty
            nonce += 1
            hash_value = cls.calculate_hash(index, previous_hash, timestamp, encrypted_data, nonce)
        
        # Save the block
        block = Block.objects.create(
            previous_hash=previous_hash,
            nonce=nonce,
            hash=hash_value,
        )
        
        # Create and save the student biodata
        student = cls.objects.create(
            block=block,
            student_id=student_id,
            encrypted_data=encrypted_data,
            created_by=user
        )
        
        return student

    def update_data(self, new_data, user):
        """Update the student data and create a new block"""
        try:
            key_obj = EncryptionKey.objects.get(user=user)
        except EncryptionKey.DoesNotExist:
            key_obj = EncryptionKey.generate_key(user)
        
        # Encrypt the new data
        encrypted_data = self.encrypt_data(new_data, key_obj)
        
        # Get the previous block
        previous_block = Block.objects.latest('id')
        previous_hash = previous_block.hash
        index = previous_block.id + 1
        
        # Create a new block
        timestamp = datetime.now().timestamp()
        nonce = 0
        hash_value = self.calculate_hash(index, previous_hash, timestamp, encrypted_data, nonce)
        
        # Simple PoW simulation
        while not hash_value.startswith('00'):
            nonce += 1
            hash_value = self.calculate_hash(index, previous_hash, timestamp, encrypted_data, nonce)
        
        # Save the new block
        block = Block.objects.create(
            previous_hash=previous_hash,
            nonce=nonce,
            hash=hash_value,
        )
        
        # Update the student record
        self.block = block
        self.encrypted_data = encrypted_data
        self.save()
        
        return self
    
class InvitationCode(models.Model):
    """Model for storing administrator invitation codes"""
    code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_invitations')
    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='used_invitation')
    
    def __str__(self):
        status = "Used" if self.is_used else "Available"
        return f"Invitation {self.code} ({status})"