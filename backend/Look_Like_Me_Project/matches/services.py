import os
import certifi
import httpx
from rest_framework import status
from django.conf import settings
import mimetypes

# Defensively remove these if they exist in your Windows environment.
# (Programs like PostgreSQL or old VPNs often set these to paths that don't exist, 
# which causes ssl.py to crash with a FileNotFoundError).
os.environ.pop('SSL_CERT_FILE', None)
os.environ.pop('SSL_CERT_DIR', None)




async def async_embed_face(payload):
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
        





# def get_image_payload(image_instance):
#     """
#     Reads a saved model's ImageField and returns file metadata.
#     """
#     # 1. Open and read the raw bytes from storage
#     with image_instance.image.open('rb') as f:
#         file_content = f.read()

#     # 2. Extract clean filename (removes path prefixes)
#     file_name = os.path.basename(image_instance.image.name)

#     # 3. Guess content type from filename ('image/jpeg', 'image/png', etc.)
#     content_type, _ = mimetypes.guess_type(image_instance.image.name)
    
#     return {
#         "file_name": file_name,
#         "file_content": file_content,
#         "content_type": content_type or "image/jpeg"  # Fallback if unknown
#     }