from auths.serializers import PublicUserProfileSerializer
from rest_framework import serializers
from rest_framework.serializers import HyperlinkedModelSerializer, Serializer

from .models import Image

class ImageSerializer(HyperlinkedModelSerializer):

    """Serializer for handling facial image uploads and file retrieval"""
    class Meta:
        model = Image
        fields = (['facial_image'])



class MatchesFeedSerializer(Serializer):
    """
    Serializer for the matches discovery feed
    Passes the parent user object (source='*') directly into the public profile serializer 
    and computes a normalized similarity score from the annotated vector distance
    """

    #  ^ default DRF behaviour of calling serializer within another is to use obj.<attribute_name, i.e., user>
    # but since the passed obj is the user itself, this make DRF skip the .attribute and directly pass the obj as is
    user = PublicUserProfileSerializer(source='*', read_only=True)
    
    # Computed field to show similarity score instead of raw vector distance
    similarity_score = serializers.SerializerMethodField()

    class Meta:
        fields = ['user', 'similarity_score']
        read_only = fields

    def get_similarity_score(self, obj): # Mapped by name
        """
        Calculates the similarity score from pgvector's cosine distance
        Since CosineDistance = 1 - cosine_similarity, the similarity is computed as (1 - distance),
        rounded to 4 decimal places
        """
        # pgvector's CosineDistance = 1 - cosine_similarity, so:
        return round(1 - obj.distance, 4)
