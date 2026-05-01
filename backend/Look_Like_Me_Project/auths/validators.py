from rest_framework import serializers

def validate_password(password):
        
    # min 8 length ✅
    # has nums
    if not any(char.isdigit() for char in password):
        raise serializers.ValidationError("Password must contain at least one number.")
    
    # has letters
    if not any(char.isalpha() for char in password):
        raise serializers.ValidationError("Password must contain at least one letter.")
    
    # has special chars
    if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for char in password):
        raise serializers.ValidationError("Password must contain at least one special character.")
    
    # no spaces or quotes
    if any(' ' in char for char in password):
        raise serializers.ValidationError("Password must not contain spaces.")
    
    if any(char in ("'", '"') for char in password):
        raise serializers.ValidationError("Password must not contain \' nor \".")
    
    # Has capital and small
    if not any(char.isupper() for char in password) or not any(char.islower() for char in password):
        raise serializers.ValidationError("Password must contain at least one uppercase and one lowercase letters.")
    
    return password