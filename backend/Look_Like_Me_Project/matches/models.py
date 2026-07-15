from django.db import models
from auths.models import User
from django.core.validators import FileExtensionValidator
import uuid

# Create your models here.
class Image(models.Model):

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        # verbose='image owner',
        related_name='images',
        )
    # verbose vs related_name: verbose is for human-readable admin display, related_name is for reverse lookups in code
    
    image = models.ImageField(
        upload_to='user_facial_images/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        )
    
    created_at = models.DateTimeField(auto_now_add=True)



    def __str__(self):
        return f"Image of {self.user.name}, path at {self.image.url}"