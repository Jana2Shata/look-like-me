from django.shortcuts import render

from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

from .models import Conversation, ConversationParticipant, Message
from .serializers import ConversationListSerializer, MessageSerializer, SendMessageSerializer
from auths.serializers import MinimalUserProfileSerializer 
from .services import ChatService
from globals.utils import get_blocked_user_ids

class MessageCursorPagination(CursorPagination):

    page_size = 25
    ordering = '-created_at'


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConversationListSerializer
    lookup_field = 'uid'

    def get_serializer_context(self):

        context = super().get_serializer_context()

        if self.request and self.request.user.is_authenticated:
            context['blocked_user_ids'] = get_blocked_user_ids(self.request.user)
        return context

    def get_queryset(self):

        user = self.request.user

        latest_message_prefetch = Prefetch(
            'messages',
            queryset=Message.objects.filter(deleted_at__isnull=True).select_related('sender').order_by('-created_at'),
            to_attr='prefetched_messages'
        )

        qs = Conversation.objects.filter(participants__user=user).prefetch_related(
            Prefetch('participants', queryset=ConversationParticipant.objects.select_related('user')),
            latest_message_prefetch
        ).distinct().order_by('-updated_at')

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(participants__user__name__icontains=search)
                & ~Q(participants__user=user)
            )

        return qs.distinct()

    @action(detail=False, methods=['post'], url_path='send')
    def send_message(self, request):

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = ChatService.send_message(
            sender=request.user,
            recipient_uid=serializer.validated_data.get('recipient_uid'),
            conversation_uid=serializer.validated_data.get('conversation_uid'),
            content=serializer.validated_data['content'],
            request=request
        )

        return Response(
            MessageSerializer(message, context=self.get_serializer_context()).data, 
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'], url_path='messages')
    def messages(self, request, uid=None):

        conversation = self.get_object()
        other_participant = next((p for p in conversation.participants.all() if p.user_id != request.user.id), None)

        queryset = conversation.messages.filter(deleted_at__isnull=True).select_related('sender', 'conversation')
        paginator = MessageCursorPagination()
        page = paginator.paginate_queryset(queryset, request)

        serializer_context = self.get_serializer_context()
        serializer = MessageSerializer(page, many=True, context=serializer_context)

        response = paginator.get_paginated_response(serializer.data)

        # response.data['other_participant'] = MinimalUserProfileSerializer(other_participant.user).data if other_participant else None

        if other_participant and other_participant.user:

            blocked_user_ids = serializer_context.get('blocked_user_ids', set())

            if other_participant.user_id in blocked_user_ids:
                response.data['other_participant'] = MinimalUserProfileSerializer.get_unavailable_payload()
            else:
                response.data['other_participant'] = MinimalUserProfileSerializer(
                    other_participant.user, context=serializer_context
                ).data
        else:
            response.data['other_participant'] = None

        return response

    @action(detail=True, methods=['post'], url_path='read')
    def mark_as_read(self, request, uid=None):

        conversation = self.get_object()
        participant = get_object_or_404(ConversationParticipant, conversation=conversation, user=request.user)
        participant.last_read_at = timezone.now()
        participant.save(update_fields=['last_read_at'])

        return Response({"status": "read"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='messages/(?P<message_uid>[^/.]+)')
    def delete_message(self, request, message_uid=None):

        ChatService.delete_own_message(user=request.user, message_uid=message_uid)
        return Response({"status": "message deleted"}, status=status.HTTP_200_OK)
