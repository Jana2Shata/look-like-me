from django.db.models import Value, FloatField
from pgvector.django import CosineDistance

def annotate_similarity_score(queryset, user):
    """
    Annotates a user queryset with cosine distance scores relative to the searching user's facial embedding
    
    - If the searching user has no image or embedding, annotates 'distance' as 'None'
    - Otherwise, performs a 'select_related('image')' optimization and computes the 
    cosine distance between each target user's embedding and the searching user's reference embedding

    Args:
        queryset: The Django queryset of User objects to annotate
        user: The searching user whose embedding serves as the reference vector

    Returns:
        QuerySet: The annotated queryset containing a 'distance' field
    """
    image = getattr(user, 'image', None)
    
    # If the searching user has no facial image or embedding, annotate distance as None
    if not image or image.embedding is None:
        return queryset.annotate(distance=Value(None, output_field=FloatField()))

    # Optimize query with select_related and annotate cosine distance using pgvector
    return queryset.select_related('image').annotate(
        distance=CosineDistance('image__embedding', image.embedding)
    )