from rest_framework import serializers

def validate_password(password):
    """
    Validates that a given password meets strict security and complexity requirements:
    - Must contain at least one number
    - Must contain at least one alphabetical letter
    - Must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?/)
    - Must not contain spaces
    - Must not contain single (') or double (") quotes
    - Must contain both at least one uppercase and one lowercase letter

    Args:
        password : The plain text password to validate

    Returns:
        str: The validated password if all checks pass

    Raises:
        serializers.ValidationError: If the password violates any complexity rule
    """

    # Has nums
    if not any(char.isdigit() for char in password):
        raise serializers.ValidationError("Password must contain at least one number.")
    
    # Has letters
    if not any(char.isalpha() for char in password):
        raise serializers.ValidationError("Password must contain at least one letter.")
    
    # Has special chars
    if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for char in password):
        raise serializers.ValidationError("Password must contain at least one special character.")
    
    # No spaces or quotes
    if any(' ' in char for char in password):
        raise serializers.ValidationError("Password must not contain spaces.")
    
    if any(char in ("'", '"') for char in password):
        raise serializers.ValidationError("Password must not contain \' nor \".")
    
    # Has capital and small letters
    if not any(char.isupper() for char in password) or not any(char.islower() for char in password):
        raise serializers.ValidationError("Password must contain at least one uppercase and one lowercase letters.")
    
    return password