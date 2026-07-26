from django.db import models
from auths.models import User
from django.core.validators import FileExtensionValidator
from pgvector.django import HalfVectorField, HnswIndex
from django.contrib.postgres.indexes import OpClass
from django.db.models.functions import Cast
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
        return f"Image of {self.user.name}, path at {self.image.url}"