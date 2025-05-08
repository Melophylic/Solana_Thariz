# biodata/services.py
from .models import Block, StudentBiodata
import hashlib
from datetime import datetime

class BlockchainService:
    """Service for blockchain operations and validation"""
    
    @staticmethod
    def validate_blockchain():
        """
        Validate the integrity of the entire blockchain
        Returns (bool, str): Tuple of (is_valid, error_message)
        """
        blocks = Block.objects.all().order_by('id')
        
        if not blocks:
            return True, "Blockchain is empty"
        
        # Check each block in sequence
        for i, block in enumerate(blocks):
            # Skip genesis block
            if i == 0:
                if block.previous_hash != "0" * 64:
                    return False, f"Invalid genesis block: {block.id}"
                
                # Even the genesis block should have student data
                try:
                    StudentBiodata.objects.get(block=block)
                except StudentBiodata.DoesNotExist:
                    # Report the issue but don't fail validation
                    # This allows the system to continue functioning while repairs are made
                    return (
                        False,
                        f"Block {block.id} has no associated student data. Run the repair_blockchain command to fix this."
                    )
                    
                continue
                    
            # Check hash points to previous block
            prev_block = blocks[i-1]
            if block.previous_hash != prev_block.hash:
                return False, f"Block {block.id} has invalid previous_hash"
            
            # Verify the hash of the current block
            try:
                student = StudentBiodata.objects.get(block=block)
                calculated_hash = StudentBiodata.calculate_hash(
                    block.id,
                    block.previous_hash,
                    block.timestamp.timestamp(),  # Convert Django datetime to timestamp
                    student.encrypted_data,
                    block.nonce
                )
                
                if calculated_hash != block.hash:
                    return False, f"Block {block.id} has invalid hash"
                    
            except StudentBiodata.DoesNotExist:
                # Report the issue but don't fail validation
                return (
                    False,
                    f"Block {block.id} has no associated student data. Run the repair_blockchain command to fix this."
                )
        
        return True, "Blockchain is valid"
    
    @staticmethod
    def get_block_details(block_id):
        """Get details of a specific block"""
        try:
            block = Block.objects.get(id=block_id)
            student = StudentBiodata.objects.get(block=block)
            
            return {
                'block_id': block.id,
                'previous_hash': block.previous_hash,
                'timestamp': block.timestamp,
                'hash': block.hash,
                'student_id': student.student_id,
                'created_by': student.created_by.username if student.created_by else "Unknown",
                'created_at': student.created_at,
            }
        except (Block.DoesNotExist, StudentBiodata.DoesNotExist):
            return None
    
    @staticmethod
    def get_blockchain_stats():
        """Get statistics about the blockchain"""
        total_blocks = Block.objects.count()
        total_students = StudentBiodata.objects.count()
        latest_block = Block.objects.order_by('-id').first()
        latest_hash = latest_block.hash if latest_block else None
        
        return {
            'total_blocks': total_blocks,
            'total_students': total_students,
            'latest_block_id': latest_block.id if latest_block else None,
            'latest_hash': latest_hash,
        }