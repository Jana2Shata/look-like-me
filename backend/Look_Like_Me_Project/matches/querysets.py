
from django.db.models import Value, FloatField
from pgvector.django import CosineDistance

def annotate_similarity_score(queryset, user):

    image = getattr(user, 'image', None)
    
    # if the searching user has no facial image or embedding, annotate distance as None
    if not image or image.embedding is None:
        return queryset.annotate(distance=Value(None, output_field=FloatField()))

    return queryset.select_related('image').annotate(
        distance=CosineDistance('image__embedding', image.embedding)
    )