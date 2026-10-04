from django.db import models
from auths.models import User
from PIL import Image as PILImage, ImageFilter
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from pgvector.django import HalfVectorField, HnswIndex
from django.contrib.postgres.indexes import OpClass
from django.db.models.functions import Cast
import io
import os
import uuid

def user_facial_image_path(instance, filename):
    # Extract file extension
    extension = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{extension}"
    return os.path.join('facial_images', new_filename)

# Create your models here.
class Image(models.Model):

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        # verbose='image owner',
        related_name='image',
        )
    # verbose vs related_name: verbose is for human-readable admin display, related_name is for reverse lookups in code
    
    facial_image = models.ImageField(
        upload_to=user_facial_image_path,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        )

    blurred_facial_image = models.ImageField(
        upload_to='blurred_facial_images/',
        null=True,
        blank=True,
        editable=False,
    )
    
    # SOURCE: https://medium.com/@simeon.emanuilov/integrating-a-vector-database-into-django-using-pgvector-72322b9debbe
    # SOURCE: https://github.com/pgvector/pgvector-python#django
    embedding = HalfVectorField(
        dimensions=2048,
        help_text="Vector embeddings of the image content",
        null=True,
        blank=True,
        )
    
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        indexes = [
            HnswIndex(
                    # use this if original vecs where ful precision but want indexing to be half
                    # useful if applying reranking after indexing
                # OpClass(Cast('embedding', HalfVectorField(dimensions=2048)), name='halfvec_cosine_ops'),
                name='embeddings_index',
                fields=['embedding'],
                    # hyper params. SOURCE: https://milvus.io/ai-quick-reference/what-are-the-key-configuration-parameters-for-an-hnsw-index-such-as-m-and-efconstructionefsearch-and-how-does-each-influence-the-tradeoff-between-index-size-build-time-query-speed-and-recall
                    m=16,
                    ef_construction=200,
                    # ef_search=100, # not supported here, only at query: `cursor.execute("SET LOCAL hnsw.ef_search = 40")`
                                        # SOURCE: https://github.com/pgvector/pgvector/issues/675
                opclasses=['halfvec_cosine_ops']
            ),
        ]


    def __str__(self):
        return f"Facial image of {self.user.name}, path at {self.facial_image.url}"

    def save(self, *args, **kwargs):
        if self.facial_image:
            self._generate_blurred_image()

        super().save(*args, **kwargs)

    def _generate_blurred_image(self):

        """
        generates a Gaussian blurred copy of facial_image using Pillow
        only runs if blurred_facial_image is not yet set or if facial_image changed
        """
        # check if facial_image file has changed or if blurred image doesn't exist
        try:
            saved_image = Image.objects.get(pk=self.pk)
            if saved_image.facial_image == self.facial_image and self.blurred_facial_image:
                return
        except Image.DoesNotExist:
            pass  

        try:
            self.facial_image.open()
            pil_img = PILImage.open(self.facial_image)
            
            # Convert non-RGB modes 
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")

            # Apply heavy Gaussian Blur (radius=50)
            blurred_img = pil_img.filter(ImageFilter.GaussianBlur(radius=80))

            # Save blurred image to memory buffer
            buffer = io.BytesIO()
            blurred_img.save(buffer, format='JPEG', quality=80)
            buffer.seek(0)

            blurred_filename = f"blurred_{uuid.uuid4()}.jpg"

            self.blurred_facial_image.save(
                blurred_filename, 
                ContentFile(buffer.read()), 
                save=False
            )
        except Exception as e:
            print(f"Error generating blurred image: {e}")


    def get_display_url(self, request=None, blurred=False):

        target_field = self.blurred_facial_image if blurred else self.facial_image
        
        if blurred and not target_field:
            return None

        url = target_field.url
        return request.build_absolute_uri(url) if request else url