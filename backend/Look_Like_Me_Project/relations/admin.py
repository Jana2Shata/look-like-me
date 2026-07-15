from django.contrib import admin
from .models import Friendship, MatchInteraction, BlockedUser

# Register your models here.
admin.site.register(Friendship)
admin.site.register(MatchInteraction)
admin.site.register(BlockedUser)