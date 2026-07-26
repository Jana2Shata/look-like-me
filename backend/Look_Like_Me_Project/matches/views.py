from django.shortcuts import render
import os
import mimetypes
from asgiref.sync import sync_to_async
from adrf.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError
from .serializers import ImageSerializer
from rest_framework import permissions
from .services import (
    async_embed_face,
    get_image_payload
    )



class EmbedFaceView(APIView):
    permission_classes = [permissions.IsAuthenticated] 


    def _build_response(self, result_dict):
        """Helper to ensure consistent frontend responses."""
        return Response({
            "success": result_dict["success"],
            "detail": result_dict["detail"],
            "reason": result_dict["reason"]
        }, status=result_dict["status_code"])




    # Change 'def' to 'async def'
    async def post(self, request):

        ser = ImageSerializer(data=request.data)
        # Notice the syntax: sync_to_async(function)(arguments)
        await sync_to_async(ser.is_valid)(raise_exception=True)  # Validate the incoming data
        
        image_instance = ser.validated_data['image']

        val_result = await async_embed_face(payload=image_instance)

        if val_result["success"]:
            try:
                # Saving the serializer to get the actual database Model instance
                image_instance = await sync_to_async(ser.save)(user=request.user)
                image_instance.embedding = val_result["embedding"]
                await image_instance.asave()
                val_result["status_code"] = status.HTTP_201_CREATED
                return self._build_response(val_result)


            except IntegrityError:
                return self._build_response({
                    "success": False,
                    "detail": "User already has an associated image.",
                    "reason": "conflict",
                    "status_code": status.HTTP_409_CONFLICT
                })
            
            except Exception as err:
                return self._build_response({
                    "success": False,
                    "detail": f"{err}",
                    "reason": "unknown_error",
                    "status_code": status.HTTP_409_CONFLICT
                })
            
        else:
            return self._build_response(val_result)





    async def put(self, request):

         # 1. Wrap the lazy evaluation and DB query in a sync function
        def get_user_image():
            # This will synchronously resolve request.user and fetch the first image
            return request.user.images # A user has only one image
            

        try:
        # 2. Await the sync function
            image_instance = await sync_to_async(get_user_image)()

        except Exception as e:

            # return Response(
            #     {"detail": "No user image found."},
            #     status=status.HTTP_404_NOT_FOUND
            # )
            return self._build_response({
                "success": False,
                "detail": "No user image found.",
                "reason": "not_found",
                "status_code": status.HTTP_404_NOT_FOUND
            })
        
        ser = ImageSerializer(image_instance, data=request.data, partial=True)
        
        # Validate
        await sync_to_async(ser.is_valid)(raise_exception=True)

        image_instance = ser.validated_data['image']

        val_result = await async_embed_face(payload=image_instance)

        if val_result["success"]:
            image_instance = await sync_to_async(ser.save)()
            image_instance.embedding = val_result["embedding"]
            await image_instance.asave()
            return self._build_response(val_result) # status code is already 200_OK

        else:
            return self._build_response(val_result)

