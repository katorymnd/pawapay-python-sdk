# src/utils/helpers.py
"""
Utility helper functions for PawaPay SDK
"""
import uuid
import re


class Helpers:
    """Utility helper class"""
    
    @staticmethod
    def generate_unique_id() -> str:
        """
        Generate a valid UUID version 4
        
        Returns:
            UUID v4 string
        """
        try:
            return str(uuid.uuid4())
        except Exception as err:
            print(f"uuid.uuid4() failed, using fallback: {str(err)}")
            # Fallback method: Manual UUID v4 generation
            import random
            return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
                '[xy]',
                lambda c: format(
                    (random.randint(0, 15) if c.group(0) == 'x' else (random.randint(0, 15) & 0x3 | 0x8)),
                    'x'
                )
            )
    
    @staticmethod
    def generate_secure_unique_id() -> str:
        """
        Alternative method using crypto module for more cryptographically secure UUIDs
        This is an alias for generate_unique_id() for backward compatibility
        
        Returns:
            UUID v4 string
        """
        return Helpers.generate_unique_id()
    
    @staticmethod
    def is_valid_uuid(uuid_str: str) -> bool:
        """
        Validate if a string is a valid UUID v4
        
        Args:
            uuid_str: The UUID to validate
            
        Returns:
            True if valid UUID v4
        """
        uuidv4_regex = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(uuidv4_regex.match(uuid_str)) 