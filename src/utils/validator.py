# src/utils/validator.py
"""
A surgical, idiomatic Python translation of the original PHP Validator class
from Katorymnd.PawaPayIntegration.Utils.
"""
import re
from typing import Any, Dict, List, Optional, Union
import decimal


class Validator:
    """Validation utilities for PawaPay SDK"""
    
    @staticmethod
    def validate_alphanumeric(input_str: str) -> str:
        """
        Validate that the input has only alphanumeric characters and spaces
        
        Args:
            input_str: Input string to validate
            
        Returns:
            input_str if valid
            
        Raises:
            ValueError with suggested correction when invalid characters are present
        """
        if not isinstance(input_str, str):
            raise ValueError("Input must be a string.")
        
        invalid_char_pattern = re.compile(r'[^a-zA-Z0-9 ]')
        if invalid_char_pattern.search(input_str):
            suggested_input = invalid_char_pattern.sub('', input_str)
            raise ValueError(
                f"The statement description contains invalid characters. "
                f"Only alphanumeric characters and spaces are allowed. "
                f"Suggested correction: '{suggested_input}'"
            )
        
        return input_str
    
    @staticmethod
    def validate_length(input_str: str, max_length: int) -> str:
        """
        Validate that the length of the input does not exceed the specified max length
        
        Args:
            input_str: Input string to validate
            max_length: Maximum allowed length
            
        Returns:
            input_str if valid
            
        Raises:
            ValueError with suggested truncation when too long
        """
        if not isinstance(input_str, str):
            raise ValueError("Input must be a string.")
        
        if not isinstance(max_length, int) or max_length < 0:
            raise ValueError("max_length must be a non-negative integer.")
        
        if len(input_str) > max_length:
            suggested_input = input_str[:max_length]
            raise ValueError(
                f"The statement description exceeds the allowed length of {max_length} characters. "
                f"Suggested correction: '{suggested_input}'"
            )
        
        return input_str
    
    @staticmethod
    def validate_statement_description(input_str: str, max_length: int = 22) -> str:
        """
        Full validation function: length + alphanumeric characters
        
        Args:
            input_str: Input string to validate
            max_length: Maximum allowed length (default: 22)
            
        Returns:
            input_str if validation passes
            
        Raises:
            ValueError if validation fails
        """
        # Step 1: Ensure input has only alphanumeric characters and spaces
        Validator.validate_alphanumeric(input_str)
        
        # Step 2: Ensure length doesn't exceed the limit
        Validator.validate_length(input_str, max_length)
        
        return input_str
    
    @staticmethod
    def validate_amount(amount: Union[str, int, float, decimal.Decimal]) -> str:
        """
        Combined regex and logical validation for amount.
        
        Mirrors the PHP behavior:
        - First checks regex: /^([0]|([1-9][0-9]{0,17}))([.][0-9]{0,2})?$/
          (up to 18 digits before decimal, up to 2 decimal places)
        - Then enforces "NotBlank" and "Positive" semantics: not blank, > 0
        
        Args:
            amount: Amount to validate
            
        Returns:
            The original amount string (trimmed)
            
        Raises:
            ValueError with descriptive message when invalid
        """
        # Normalize input, preserve trimmed string for messages
        amount_str = '' if amount is None else str(amount).strip()
        
        # pawaPay's pattern: up to 18 digits before decimal, optional decimal with up to 2 places
        pattern = re.compile(r'^([0]|([1-9][0-9]{0,17}))([.][0-9]{0,2})?$')
        
        # Validate presence
        if not amount_str:
            raise ValueError("This value should not be blank.")
        
        # Validate pattern
        if not pattern.match(amount_str):
            raise ValueError(
                f"The amount '{amount_str}' is invalid. "
                f"The amount must be a number with up to 18 digits before the decimal point "
                f"and up to 2 decimal places."
            )
        
        # Convert to Decimal for accurate numeric validation
        try:
            from decimal import Decimal, InvalidOperation
            numeric = Decimal(amount_str)
        except (InvalidOperation, ValueError):
            raise ValueError(f"The amount '{amount_str}' is not a valid number.")
        
        # Enforce Positive (disallows zero)
        if numeric <= 0:
            raise ValueError("This value should be positive.")
        
        return amount_str
    
    @staticmethod
    def joi_validate(data: Any, constraints: List[Dict[str, Any]]) -> Any:
        """
        General lightweight validator to mimic Symfony behavior for simple constraints.
        
        Constraint descriptor examples:
            {'type': 'NotBlank', 'message': '...'}
            {'type': 'Length', 'max': 50, 'max_message': '...'}
            {'type': 'Regex', 'pattern': '^[a-z]+$', 'message': '...'}
            {'type': 'Positive', 'message': '...'}
        
        The function throws the first encountered violation as a ValueError.
        
        Args:
            data: Data to validate
            constraints: List of constraint dictionaries
            
        Returns:
            data when valid
            
        Raises:
            ValueError with first violation message
        """
        for constraint in constraints:
            if not constraint or 'type' not in constraint:
                continue
            
            constraint_type = constraint['type']
            
            if constraint_type == 'NotBlank':
                if (data is None or 
                    (isinstance(data, str) and not data.strip())):
                    raise ValueError(constraint.get('message', 'This value should not be blank.'))
            
            elif constraint_type == 'Positive':
                try:
                    numeric = float(data) if not isinstance(data, (int, float)) else data
                    if not isinstance(numeric, (int, float)) or numeric <= 0:
                        raise ValueError(constraint.get('message', 'This value should be positive.'))
                except (ValueError, TypeError):
                    raise ValueError(constraint.get('message', 'This value should be positive.'))
            
            elif constraint_type == 'Length':
                if isinstance(data, str):
                    if 'max' in constraint and constraint['max'] is not None:
                        if len(data) > constraint['max']:
                            msg = constraint.get('max_message', 
                                f"This value is too long. It should have {constraint['max']} characters or less.")
                            msg = msg.replace('{{ limit }}', str(constraint['max']))
                            raise ValueError(msg)
                    
                    if 'min' in constraint and constraint['min'] is not None:
                        if len(data) < constraint['min']:
                            msg = constraint.get('min_message',
                                f"This value is too short. It should have {constraint['min']} characters or more.")
                            msg = msg.replace('{{ limit }}', str(constraint['min']))
                            raise ValueError(msg)
            
            elif constraint_type == 'Regex':
                pattern = constraint.get('pattern')
                if pattern:
                    if isinstance(pattern, str):
                        regex = re.compile(pattern)
                    else:
                        regex = pattern
                    
                    if not isinstance(data, str) or not regex.match(data):
                        raise ValueError(constraint.get('message', 'This value is not valid.'))
        
        return data
    
    @staticmethod
    def validate_metadata_item_count(metadata: List[Any]) -> List[Any]:
        """
        Validate that the number of metadata items does not exceed 10
        
        Args:
            metadata: Metadata list to validate
            
        Returns:
            metadata if valid
            
        Raises:
            ValueError when count > 10
        """
        if not isinstance(metadata, list):
            raise ValueError("Metadata must be a list.")
        
        if len(metadata) > 10:
            raise ValueError(
                f"Number of metadata items must not be more than 10. "
                f"You provided {len(metadata)} items."
            )
        
        return metadata
    
    @staticmethod
    def validate_metadata_field(field_name: str, field_value: str) -> Dict[str, str]:
        """
        Validate individual metadata fields: field_name and field_value
        
        Args:
            field_name: Metadata field name
            field_value: Metadata field value
            
        Returns:
            Dictionary with validated field_name and field_value
            
        Raises:
            ValueError if validation fails
        """
        # Define constraints for field_name
        field_name_constraints = [
            {'type': 'NotBlank', 'message': 'Metadata field name cannot be blank.'},
            {'type': 'Length', 'max': 50, 
             'max_message': 'Metadata field name cannot exceed {{ limit }} characters.'},
            {'type': 'Regex', 'pattern': r'^[a-zA-Z0-9_ ]+$',
             'message': 'Metadata field name can only contain alphanumeric characters, underscores, and spaces.'}
        ] 
        
        # Define constraints for field_value
        field_value_constraints = [
            {'type': 'NotBlank', 'message': 'Metadata field value cannot be blank.'},
            {'type': 'Length', 'max': 100,
             'max_message': 'Metadata field value cannot exceed {{ limit }} characters.'},
            {'type': 'Regex', 'pattern': r'^[a-zA-Z0-9_\-., ]+$',
             'message': 'Metadata field value can only contain alphanumeric characters, '
                        'underscores, hyphens, periods, commas, and spaces.'}
        ]
        
        # Validate field_name
        Validator.joi_validate(field_name, field_name_constraints)
        
        # Validate field_value
        Validator.joi_validate(field_value, field_value_constraints)
        
        return {
            'field_name': field_name,
            'field_value': field_value
        }