# biodata/advanced_repair.py

from django.core.management.base import BaseCommand
from .models import Block, StudentBiodata, EncryptionKey
from django.contrib.auth.models import User
import hashlib
from datetime import datetime
import json
from cryptography.fernet import Fernet

def detect_missing_blocks():
    """
    Detects gaps in the block chain
    Returns a list of missing block IDs
    """
    all_blocks = Block.objects.all().order_by('id')
    
    if not all_blocks:
        return []
    
    # Get a list of all block IDs
    block_ids = [block.id for block in all_blocks]
    
    # Find gaps in the sequence
    missing_ids = []
    min_id = min(block_ids)
    max_id = max(block_ids)
    
    for i in range(min_id, max_id + 1):
        if i not in block_ids:
            missing_ids.append(i)
    
    return missing_ids

def repair_missing_blocks():
    """
    Repairs missing blocks by creating placeholder blocks
    Returns a tuple of (success, message, fixed_blocks)
    """
    missing_ids = detect_missing_blocks()
    
    if not missing_ids:
        return True, "No missing blocks detected", []
    
    fixed_blocks = []
    
    # Get a superuser to be the owner of placeholder records
    superuser = User.objects.filter(is_superuser=True).first()
    if not superuser:
        return False, "No superuser found to create placeholder blocks", []
    
    # Get or create an encryption key
    try:
        key = EncryptionKey.objects.get(user=superuser)
    except EncryptionKey.DoesNotExist:
        key = EncryptionKey.generate_key(superuser)
    
    # Process each missing block ID
    for missing_id in missing_ids:
        success = create_placeholder_block(missing_id, superuser, key)
        if success:
            fixed_blocks.append(missing_id)
    
    if fixed_blocks:
        # After creating missing blocks, we need to fix the hash chain
        fix_hash_chain()
        return True, f"Created {len(fixed_blocks)} missing blocks and repaired hash chain", fixed_blocks
    else:
        return False, "Failed to create missing blocks", []

def create_placeholder_block(block_id, superuser, key):
    """
    Creates a placeholder block with the given ID
    """
    try:
        # Find the blocks before and after this ID
        prev_blocks = Block.objects.filter(id__lt=block_id).order_by('-id')
        next_blocks = Block.objects.filter(id__gt=block_id).order_by('id')
        
        prev_block = prev_blocks.first() if prev_blocks else None
        next_block = next_blocks.first() if next_blocks else None
        
        if not prev_block:
            # Can't create a block without a previous block
            return False
        
        # Create a placeholder block
        placeholder_block = Block(
            id=block_id,
            previous_hash=prev_block.hash,
            nonce=0,
            hash="placeholder"  # Temporary hash, will be updated
        )
        placeholder_block.save()
        
        # Create placeholder student data
        placeholder_data = {
            'nama': f'PLACEHOLDER FOR MISSING BLOCK {block_id}',
            'nisn': '999999999',
            'kelahiran': 'PLACEHOLDER, 01 JANUARY 2000',
            'kelamin': 'LAKI-LAKI',
            'alamat': 'PLACEHOLDER ADDRESS FOR MISSING BLOCK'
        }
        
        # Encrypt the data
        json_data = json.dumps(placeholder_data)
        fernet = Fernet(key.key)
        encrypted_data = fernet.encrypt(json_data.encode())
        
        # Create a student record
        placeholder_student = StudentBiodata(
            block=placeholder_block,
            student_id=f'PH{block_id:06d}',  # Placeholder ID
            encrypted_data=encrypted_data,
            created_by=superuser
        )
        placeholder_student.save()
        
        # Calculate a proper hash for the block
        timestamp = placeholder_block.timestamp.timestamp()
        calculated_hash = calculate_hash(
            block_id, 
            prev_block.hash,
            timestamp,
            encrypted_data
        )
        
        placeholder_block.hash = calculated_hash
        placeholder_block.save()
        
        return True
    
    except Exception as e:
        print(f"Error creating placeholder block {block_id}: {str(e)}")
        return False

def calculate_hash(index, previous_hash, timestamp, data, nonce=0):
    """Calculate a SHA-256 hash with proof of work"""
    value = str(index) + str(previous_hash) + str(timestamp) + str(data) + str(nonce)
    hash_value = hashlib.sha256(value.encode()).hexdigest()
    
    # Simple proof of work - find a hash that starts with '00'
    while not hash_value.startswith('00'):
        nonce += 1
        value = str(index) + str(previous_hash) + str(timestamp) + str(data) + str(nonce)
        hash_value = hashlib.sha256(value.encode()).hexdigest()
    
    return hash_value

def fix_hash_chain():
    """
    Ensures all blocks have correct previous_hash values
    """
    blocks = Block.objects.all().order_by('id')
    
    # Skip if there are less than 2 blocks
    if len(blocks) < 2:
        return
    
    # Ensure each block points to the previous block
    for i in range(1, len(blocks)):
        current_block = blocks[i]
        prev_block = blocks[i-1]
        
        # If the current block doesn't point to the correct previous hash
        if current_block.previous_hash != prev_block.hash:
            # Update the previous_hash
            current_block.previous_hash = prev_block.hash
            
            # Recalculate the current block's hash
            try:
                student = StudentBiodata.objects.get(block=current_block)
                timestamp = current_block.timestamp.timestamp()
                
                # Start with the existing nonce
                nonce = current_block.nonce
                
                # Calculate new hash
                value = str(current_block.id) + str(prev_block.hash) + str(timestamp) + str(student.encrypted_data) + str(nonce)
                hash_value = hashlib.sha256(value.encode()).hexdigest()
                
                # Simple proof of work
                while not hash_value.startswith('00'):
                    nonce += 1
                    value = str(current_block.id) + str(prev_block.hash) + str(timestamp) + str(student.encrypted_data) + str(nonce)
                    hash_value = hashlib.sha256(value.encode()).hexdigest()
                
                # Update the block
                current_block.nonce = nonce
                current_block.hash = hash_value
                current_block.save()
                
            except StudentBiodata.DoesNotExist:
                # If there's no student data, we can't calculate a proper hash
                # This should not happen if all blocks have associated student data
                pass

# Create a management command to run the advanced repair
class Command(BaseCommand):
    help = 'Repairs blockchain with missing blocks'

    def handle(self, *args, **options):
        success, message, fixed_blocks = repair_missing_blocks()
        
        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.WARNING(message))
            
        if fixed_blocks:
            self.stdout.write(f"Fixed blocks: {', '.join(map(str, fixed_blocks))}")