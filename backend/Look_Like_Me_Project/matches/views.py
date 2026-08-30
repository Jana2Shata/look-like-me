from asgiref.sync import sync_to_async
from adrf.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import IntegrityError
from pgvector.django import CosineDistance
import time
from django.conf import settings
from django.db.models import Prefetch

from .serializers import (
    ImageSerializer,
    MatchesFeedSerializer,
    )
from .services import (
    async_embed_face,
    )
from .models import Image
from auths.models import User
from relations.models import MatchInteraction



class EmbedFaceView(APIView):
    permission_classes = [permissions.IsAuthenticated] 


    def _build_response(self, result_dict):
        """Helper to ensure consistent frontend responses."""
        return Response({
            "success": result_dict["success"],
            "detail": result_dict["detail"],
            "reason": result_dict["reason"]
        }, status=result_dict["status_code"])


    def _get_user_image(self, request):
                "Helper to wrap the lazy evaluation and DB query in a sync function"
                # synchronously resolve request.user and fetch the first image
                return request.user.image # A user has only one image




    # Change 'def' to 'async def'
    async def post(self, request):

        ser = ImageSerializer(data=request.data)
        # Notice the syntax: sync_to_async(function)(arguments)
        await sync_to_async(ser.is_valid)(raise_exception=True)  # Validate the incoming data
        
        image_instance = ser.validated_data['facial_image']

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
                    "detail": "User already has an associated facial image.",
                    "reason": "conflict",
                    "status_code": status.HTTP_409_CONFLICT
                })
            
            except Exception as err:
                return self._build_response({
                    "success": False,
                    "detail": f"{err}",
                    "reason": "unknown_error",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
                })
            
        else:
            return self._build_response(val_result)





    async def put(self, request):          

        try:
        # Awaiting the sync function
            image_instance = await sync_to_async(self._get_user_image)(request)

        except Exception as e:

            return self._build_response({
                "success": False,
                "detail": "No facial image found.",
                "reason": "not_found",
                "status_code": status.HTTP_404_NOT_FOUND
            })
        
        ser = ImageSerializer(image_instance, data=request.data, partial=True)
        
        # Validate
        await sync_to_async(ser.is_valid)(raise_exception=True)

        image_instance = ser.validated_data['facial_image']

        val_result = await async_embed_face(payload=image_instance)

        if val_result["success"]:
            image_instance = await sync_to_async(ser.save)()
            image_instance.embedding = val_result["embedding"]
            await image_instance.asave()
            return self._build_response(val_result) # status code is already 200_OK

        else:
            return self._build_response(val_result)



    async def get(self, request):

        try:
            image_instance = await sync_to_async(self._get_user_image)(request)

        except Exception as e:
            return Response({
                "detail": "User has no associated facial image.",
                "data": None,
            }, status=status.HTTP_404_NOT_FOUND)


        serializer = ImageSerializer(image_instance, context={'request': request})

        return Response({
            "detail": "Facial image retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)



    async def delete(self, request):

        try:
            image_instance = await sync_to_async(self._get_user_image)(request)

        except Exception as e:
            return Response({
                "detail": "User has no associated facial image.",
            }, status=status.HTTP_404_NOT_FOUND)

        await image_instance.adelete()

        return Response({
            "detail": "Facial image deleted successfully.",
        }, status=status.HTTP_200_OK)

    



class MatchesFeed(APIView):
    permission_classes = [permissions.IsAuthenticated] 

    similarity_threshold = 1- settings.AI_HYPER_PARAMS['COSINE_SIM_THRESHOLD'] # convert into distance metric
    top_k = settings.AI_HYPER_PARAMS['TOP_K']

    def get(self, request):

        user = request.user

        try:
            _ = user.image
        except Image.DoesNotExist:
            return Response(
                {"detail": "User has no associated facial image.",
                 'Search_time': None,
                 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )

        start_time = time.perf_counter()

        images_distances = Image.objects.select_related('user' # efficiently fetch user oand its related objects
            ).annotate(
                distance=CosineDistance('embedding', user.image.embedding)
                    ).filter(distance__lt=self.similarity_threshold).order_by('distance'
                        ).exclude(user=user)[:self.top_k # Exclude the current user's image and limit to top 5 matches
                            ].prefetch_related(Prefetch( # Prefetch the received interactions of each matched user from the current request's user to optimize database lookups
                                lookup='user__received_interactions',
                                queryset=MatchInteraction.objects.filter(sender=user),
                            ))

        end_time = time.perf_counter()

        if len(images_distances) < 1:
            return Response(
                {'detail': f'No matches found at threshold {1-self.similarity_threshold}',
                 'Search_time': f'{(end_time-start_time):.6f} seconds',
                 'data': None},
                status=status.HTTP_200_OK
            )

        # serialize the matched images
        serializer = MatchesFeedSerializer(images_distances, many=True, context={'request': request})

        return Response(
            {'detail': 'Matches found and retrieved successfully.',
             'Search_time': f'{(end_time-start_time):.6f} seconds',
             'data': serializer.data},
             status=status.HTTP_200_OK
        )




class TempMatchesFeed(APIView):
    permission_classes = [] 

    similarity_threshold = 1- settings.AI_HYPER_PARAMS['COSINE_SIM_THRESHOLD'] # convert into distance metric
    top_k = settings.AI_HYPER_PARAMS['TOP_K']

    def get(self, request, id):

        try:
            user = User.objects.get(id=id)

        except:
            return Response(
                {"detail": "No user with this id."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            _ = user.image
        except Image.DoesNotExist:
            return Response(
                {"detail": "User has no associated facial image.",
                 'Search_time': None,
                 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )

        start_time = time.perf_counter()

        images_distances = Image.objects.select_related('user' # efficiently fetch user oand its related objects
            ).annotate(
                distance=CosineDistance('embedding', user.image.embedding)
                    ).filter(distance__lt=self.similarity_threshold).order_by('distance'
                        ).exclude(user=user)[:self.top_k]  # Exclude the current user's image and limit to top 5 matches

        end_time = time.perf_counter()

        if len(images_distances) < 1:
            return Response(
                {'detail': f'For user {user}, no matches found at threshold {1-self.similarity_threshold}',
                'Search_time': f'{(end_time-start_time):.6f} seconds',
                'data': None},
                status=status.HTTP_200_OK
            )

        # serialize the matched images
        serializer = MatchesFeedSerializer(images_distances, many=True, context={'request': request})

        return Response(
            {'detail': 'Matches found and retrieved successfully.',
             'Search_time': f'{(end_time-start_time):.6f} seconds',
             'data': serializer.data},
             status=status.HTTP_200_OK
        )