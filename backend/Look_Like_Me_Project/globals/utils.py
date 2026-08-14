from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.db import IntegrityError

# Source - https://stackoverflow.com/a/74504921
# Posted by Alvaro Rodriguez Scelza
# Retrieved 2026-08-14, License - CC BY-SA 4.0

# def integrity_exception_handler(exc, context):
#     """
#     Handle Django IntegrityError as an accepted exception by DRF.
#     """
#     if isinstance(exc, IntegrityError):
#         exc = DRFValidationError(detail=exc)
#         response = exception_handler(exc, context)
#     #     # if response is not None:
#     #     #     response.data.append(context.get('view').get_exception_message())
#     # return f"{exc}"
#     return response

#     # Call REST framework's default exception handler first,
#     # to get the standard error response.
#     response = exception_handler(exc, context)

#     # Now add the HTTP status code to the response.
#     if response is not None:
#         response.data['status_code'] = response.status_code

#     return response
