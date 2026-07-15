from knox.auth import TokenAuthentication

class KnoxTokenOnlyMixin:
    """
    Apply this to any view to strictly limit authentication to Knox tokens,
    effectively ignoring Session cookies for this endpoint.
    """
    authentication_classes = [TokenAuthentication]