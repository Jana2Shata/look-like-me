from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from .managers import UserManager
import uuid


class User(AbstractUser):
    """
    Extending AbstractBaseUser instead of Model because:
    - It provides built-in password hashing (never store plain text passwords)
    - It integrates with Django's auth system (sessions, permissions, decorators)
    - It gives us `last_login` tracking for free
    - AbstractUser (vs AbstractBaseUser) gives shortcuts to required auth fields
    """

    username = first_name = last_name = None

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=200)

    email = models.EmailField(unique=True)
    # password field is inherited from AbstractBaseUser
    # AbstractBaseUser stores it hashed automatically via set_password()

    class GenderChoices(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'

    gender =models.CharField(
        null=True,
        blank=False,
        max_length=6,
        choices=GenderChoices.choices)
    
    birth_date = models.DateField(
        null=True,
        blank=False,
    ) # not datetime
    country = models.CharField(
        max_length=100,
        null=True,
        blank=False,)

    profile_photo = models.ImageField( # so Django validates it's a real image
        upload_to='profile_photos/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        # validators enforce allowed formats at app layer
        )
    bio = models.TextField(
        max_length=300,
        null=True,
        blank=False,
        default='',
    )

    
    date_joined = models.DateTimeField(auto_now_add=True)
    # set once on creation, never updated

    # friends = models.ManyToManyField(
    #     'self',
    #     through=Friendship,
    #     symmetrical=False,
    #     through_fields=('sender', 'receiver'),
    # ) CONSIDER: how to distingush friendship symmetry between 'pending and 'accepted'

    # Required by AbstractBaseUser
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name'] # what the admin must provide

    objects = UserManager()
        

    def __str__(self):
        return self.name
    
    def get_full_name(self):
        
        
        return str(self)


    def get_short_name(self):
        
        return str(self)


