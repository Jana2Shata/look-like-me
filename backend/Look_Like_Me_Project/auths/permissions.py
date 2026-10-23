from rest_framework import permissions

class IsProfileComplete(permissions.BasePermission):
    """
    Allows access only to users who have completed their required profile fields
    """
    message = "Profile completion required. Please update your gender, and country"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user
        
        # Check if required fields are filled
        if not user.gender or not user.country:
            return False
            
        return True