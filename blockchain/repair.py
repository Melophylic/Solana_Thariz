# biodata/repair.py
from django.core.management.base import BaseCommand
from .models import Block, StudentBiodata
import hashlib
from datetime import datetime
import json

def repair_blockchain():
    """
    Repairs blockchain integrity issues by fixing orphaned blocks
    Returns a tuple of (success, message, fixed_blocks)
    """
    fixed_blocks = []
    
    # Find all orphaned blocks (blocks without student data)
    all_blocks = Block.objects.all().order_by('id')
    orphaned_blocks = []
    
    for block in all_blocks:
        try:
            # Check if there's a student record for this block
            StudentBiodata.objects.get(block=block)
        except StudentBiodata.DoesNotExist:
            orphaned_blocks.append(block)
    
    if not orphaned_blocks:
        return True, "No orphaned blocks found.", []
    
    # Attempt to repair each orphaned block
    for orphaned_block in orphaned_blocks:
        fixed = repair_orphaned_block(orphaned_block)
        if fixed:
            fixed_blocks.append(orphaned_block.id)
    
    # If we fixed all orphaned blocks
    if len(fixed_blocks) == len(orphaned_blocks):
        return True, f"Successfully repaired {len(fixed_blocks)} orphaned blocks.", fixed_blocks
    else:
        return False, f"Repaired {len(fixed_blocks)} blocks, but {len(orphaned_blocks) - len(fixed_blocks)} remain orphaned.", fixed_blocks

def repair_orphaned_block(orphaned_block):
    """
    Attempts to repair a single orphaned block by either:
    1. Deleting it (if it's not essential to the chain)
    2. Creating a placeholder student record for it
    
    Returns True if fixed, False otherwise
    """
    # Check if this block is part of the main chain
    try:
        # Is any block pointing to this one as previous?
        next_block = Block.objects.get(previous_hash=orphaned_block.hash)
        
        # If yes, this block is part of the chain and needed
        # Create a placeholder student record
        placeholder_data = {
            'nama': f'PLACEHOLDER FOR BLOCK {orphaned_block.id}',
            'nisn': '000000000',
            'kelahiran': 'UNKNOWN, 01 JANUARY 2000',
            'kelamin': 'LAKI-LAKI',
            'alamat': 'PLACEHOLDER ADDRESS'
        }
        
        # Encrypt the placeholder data (using a system-wide encryption key)
        from django.contrib.auth.models import User
        from .models import EncryptionKey
        
        # Get a superuser to be the owner
        superuser = User.objects.filter(is_superuser=True).first()
        
        if not superuser:
            return False
            
        try:
            key = EncryptionKey.objects.get(user=superuser)
        except EncryptionKey.DoesNotExist:
            key = EncryptionKey.generate_key(superuser)
            
        json_data = json.dumps(placeholder_data)
        from cryptography.fernet import Fernet
        fernet = Fernet(key.key)
        encrypted_data = fernet.encrypt(json_data.encode())
        
        # Create the student record
        StudentBiodata.objects.create(
            block=orphaned_block,
            student_id=f'PH{orphaned_block.id:06d}',  # Placeholder ID
            encrypted_data=encrypted_data,
            created_by=superuser
        )
        
        return True
        
    except Block.DoesNotExist:
        # No next block depends on this one, so it's safe to delete
        orphaned_block.delete()
        return True
    except Exception as e:
        print(f"Error repairing block {orphaned_block.id}: {str(e)}")
        return False

# Create a management command to run the repair
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Repairs blockchain integrity issues'

    def handle(self, *args, **options):
        success, message, fixed_blocks = repair_blockchain()
        
        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.WARNING(message))
            
        if fixed_blocks:
            self.stdout.write(f"Fixed blocks: {', '.join(map(str, fixed_blocks))}")