"""
Tests for ViewSet serializer info extraction.
"""
from rest_framework import viewsets, serializers
from dj_urls_panel.utils import get_drf_serializer_info


class SampleSerializer(serializers.Serializer):
    """Sample serializer for testing."""
    id = serializers.IntegerField()
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()


class SampleViewSet(viewsets.ModelViewSet):
    """Sample ViewSet for testing."""
    serializer_class = SampleSerializer


def test_viewset_serializer_extraction():
    """Test that serializer info can be extracted from a ViewSet."""
    info = get_drf_serializer_info(SampleViewSet)
    
    assert info is not None, "Should extract serializer info from ViewSet"
    assert info['serializer_name'] == 'SampleSerializer'
    assert len(info['fields']) == 3
    
    field_names = [f['name'] for f in info['fields']]
    assert 'id' in field_names
    assert 'name' in field_names
    assert 'email' in field_names
