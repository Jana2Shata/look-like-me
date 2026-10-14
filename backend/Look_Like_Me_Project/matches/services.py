import os
import certifi
import httpx
from rest_framework import status
from django.conf import settings


# Defensively remove these if they exist in your Windows environment.
# (Programs like PostgreSQL or old VPNs often set these to paths that don't exist, 
# which causes ssl.py to crash with a FileNotFoundError).
os.environ.pop('SSL_CERT_FILE', None)
os.environ.pop('SSL_CERT_DIR', None)


async def async_embed_face(payload):
    """
    Sends a facial image payload asynchronously to the AI embedding service 
    and returns the resulting embeddings or rejection details

    Args:
        payload: The uploaded image file object (containing name, read method, and content_type)

    Returns:
        A structured dictionary containing:
            - success (bool): True if accepted, False otherwise
            - detail (str): Descriptive message from the AI service
            - reason (str|None): Rejection reason if applicable
            - embedding (list|None): 2048-dimensional vector embedding if successful
            - status_code (int): Corresponding HTTP status code
    """
    ai_url = settings.HEADLESS_AI_URLS['embed']
    
    # Using an async context manager ensures connections are closed properly
    async with httpx.AsyncClient(verify=certifi.where()) as client:

        file = {
            "profile_photo": (payload.name, payload.read(), payload.content_type)
        }

        try:
            # Note the 'await' keyword here
            response = await client.post(url=ai_url, files=file, timeout=15.0)

            response.raise_for_status()
            data = response.json()
            
            if data.get("accepted"):

                return {
                    "success": True,
                    "detail": data.get("details"),
                    "reason": None,
                    "embedding": data.get("embedding"),
                    "status_code": status.HTTP_200_OK
                }


            # AI processed it but rejected the image (e.g., no face found, blurry)
            return {
                "success": False,
                "detail": data.get("details"),
                "reason": data.get("reason"),
                "embedding": None,
                "status_code": status.HTTP_400_BAD_REQUEST
            }
            
        except httpx.TimeoutException:
            return {
                "success": False, 
                "detail": "AI service timed out while analyzing the image.", 
                "reason": "timeout",
                "status_code": status.HTTP_408_REQUEST_TIMEOUT
            }
        except Exception as err:
            return {
                "success": False, 
                "detail": f"AI service is currently unavailable. {err}", 
                "reason": "service_unavailable",
                "status_code": status.HTTP_503_SERVICE_UNAVAILABLE
            }
        
