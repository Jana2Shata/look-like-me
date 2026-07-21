from django.shortcuts import render
import os
import mimetypes
from asgiref.sync import sync_to_async
from adrf.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ImageSerializer
from rest_framework import permissions
from .services import (
    async_validate_face,
    async_embed_face,
    get_image_payload
    )
class ValidateFaceView(APIView):
    permission_classes = [permissions.IsAuthenticated] 

    # Change 'def' to 'async def'
    async def post(self, request):

        ser = ImageSerializer(data=request.data)
        # Notice the syntax: sync_to_async(function)(arguments)
        await sync_to_async(ser.is_valid)(raise_exception=True)  # Validate the incoming data
        
        image_file = ser.validated_data['image']

        # Pass the file object itself to the service
        payload = {
            "file_name": image_file.name,
            "file_content": image_file.read(),
            "content_type": image_file.content_type
        }
        
        # Await the async service call
        val_result = await async_validate_face(payload)
        
        if not val_result["success"]:
            return Response({"error": val_result["error"]}, status=val_result["status_code"])
            

        await sync_to_async(ser.save)(user=request.user)  # Save the validated image to the database

        return Response({
            "detail": "Image validated and saved successfully.",
        }, status=status.HTTP_201_CREATED)
    






class EmbedFaceView(APIView):
    permission_classes = [permissions.IsAuthenticated] 

    # Change 'def' to 'async def'
    async def post(self, request):

        # 1. Wrap the lazy evaluation and DB query in a sync function
        def get_user_image():
            # This will synchronously resolve request.user and fetch the first image
            return request.user.images # A user has only one image
            
        # 2. Await the sync function
        image_instance = await sync_to_async(get_user_image)()

        if not image_instance or not image_instance.image:
            return Response(
                {"detail": "No user image found."},
                status=status.HTTP_404_NOT_FOUND
            )

       
        payload = await sync_to_async(get_image_payload)(image_instance)
        
        # Await the async service call
        val_result = await async_embed_face(payload)
        
        if not val_result["success"]:
            return Response({"error": val_result["error"]}, status=val_result["status_code"])
            
        image_instance.embedding = val_result["data"].get("embedding")
        await image_instance.asave()
        

        return Response({
            "detail": "Image embedded successfully.",
        }, status=status.HTTP_200_OK)