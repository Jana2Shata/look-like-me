
# SOURCE: https://pypi.org/project/django-seeding/#user-content-seeder

from django_seeding import seeders
from django_seeding.seeder_registry import SeederRegistry 

from auths.models import User
from matches.models import Image
from matches.services import async_embed_face

import os
import mimetypes
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile

images_path = "../test_images/"

images_names = os.listdir(images_path)


@SeederRegistry.register
class DummyUserSeeder(seeders.Seeder):
    id = 'DummyUserSeeder'
    priority = 1
    
    def seed(self):

        for image_name in images_names:
            
            base_name = image_name.split('.')[0]

            print(f"Seeding user and image for: {base_name}")

            relative_path = os.path.join(images_path, image_name)

            # 1. Automatically detect content type (e.g., 'image/jpeg', 'image/png')
            content_type, _ = mimetypes.guess_type(relative_path)
            content_type = content_type or 'image/jpg'  # fallback if detection fails

            with open(relative_path, 'rb') as img_file:
                payload = SimpleUploadedFile(
                    name=image_name,
                    content=img_file.read(),
                    content_type=content_type
                )

                response = embed_face(payload=payload)

                if response.get("success"):
                    # create user instance
                    user = User.objects.create(
                        name=base_name,
                        email=f"{base_name}@dummy.com",
                        password="Password@123"
                    )

                    # create associated image instance
                    image = Image.objects.create(
                        user=user,
                        image=File(img_file, name=base_name),
                        embedding=response.get("embedding")
                    )

                else:
                    print(f"Failed to embed image for {base_name}: {response.get('detail')}")






import os
import certifi
import httpx
import requests
from rest_framework import status
from django.conf import settings
import mimetypes

# Defensively remove these if they exist in your Windows environment.
# (Programs like PostgreSQL or old VPNs often set these to paths that don't exist, 
# which causes ssl.py to crash with a FileNotFoundError).
os.environ.pop('SSL_CERT_FILE', None)
os.environ.pop('SSL_CERT_DIR', None)




def embed_face(payload):
    ai_url = settings.HEADLESS_AI_URLS['embed']
    

    file = {
        "profile_photo": (payload.name, payload.read(), payload.content_type)
    }

    try:
        # Note the 'await' keyword here
        response = requests.post(url=ai_url, files=file, timeout=15.0)

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