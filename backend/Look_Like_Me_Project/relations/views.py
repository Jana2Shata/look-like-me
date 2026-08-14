from django.shortcuts import render
from rest_framework import mixins, viewsets, generics
from rest_framework import status, permissions
from django.db import IntegrityError
from rest_framework.response import Response

from .models import MatchInteraction, Friendship,  BlockedUser
from .serializers import MatchInteractionSerializer
from .mixins import MatchInteractionMixin


class LikesView(MatchInteractionMixin):
    type = 'like'


class SavesView(MatchInteractionMixin):
    type = 'save'
    