from rest_framework import permissions, exceptions

class IsProfileComplete(permissions.BasePermission):
    """
    Allows access only to users who have completed their required profile fields
    """
    message = "Profile completion required. Please update your gender, country, and birth date"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user
        
        # Check if required fields (gender, country, birth_date) are filled
        if not user.gender or not user.country or not user.birth_date:
            raise exceptions.PermissionDenied(
                detail={
                    "code": "profile_incomplete",
                    "detail": "Profile completion required. Please update your gender, country, and birth date."
                }
            )
            
        return True