
from rest_framework import serializers
from rest_framework.serializers import HyperlinkedModelSerializer, ModelSerializer
from .models import Image
from auths.serializers import PublicUserProfileSerializer

class ImageSerializer(HyperlinkedModelSerializer):

    class Meta:
        model = Image
        fields = (['image'])



class MatchesFeedSerializer(ModelSerializer):
    # Nest the public user data
    user = PublicUserProfileSerializer(read_only=True)
    
    # Using ImageField ensures DRF automatically handles URL generation
        # Cannot use the serializer, because then DRF will interpret it as another related object rather than a field
    image = serializers.ImageField() 
    
    # Computed field to show similarity score instead of raw vector distance
    similarity_score = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['image', 'user', 'similarity_score']

    def get_similarity_score(self, obj): # Mapped by name
        # pgvector's CosineDistance = 1 - cosine_similarity, so:
        return round(1 - obj.distance, 4)