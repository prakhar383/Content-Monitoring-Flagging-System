from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Keyword, Flag
from .serializers import (
    KeywordSerializer,
    FlagSerializer,
    FlagStatusUpdateSerializer,
)
from .services import ScanService


# ------------------------------------------------------------------ #
# GET  /api/keywords/  → list all keywords
# POST /api/keywords/  → create a keyword
# ------------------------------------------------------------------ #
class KeywordListView(APIView):

    def get(self, request):
        keywords   = Keyword.objects.all()
        serializer = KeywordSerializer(keywords, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = KeywordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


# ------------------------------------------------------------------ #
# POST /api/scan/  → trigger a full scan
# ------------------------------------------------------------------ #
class ScanView(APIView):

    def post(self, request):
        results = ScanService.run_scan()
        return Response({
            'message' : 'Scan completed successfully.',
            'results' : results,
        }, status=status.HTTP_200_OK)


# ------------------------------------------------------------------ #
# GET /api/flags/  → list all flags
# ------------------------------------------------------------------ #
class FlagListView(APIView):

    def get(self, request):
        # Allow filtering by status e.g. /api/flags/?status=pending
        status_filter = request.query_params.get('status', None)

        flags = Flag.objects.select_related(
            'keyword', 'content_item'
        ).all()

        if status_filter:
            flags = flags.filter(status=status_filter)

        # Order by score descending — highest confidence matches first
        flags = flags.order_by('-score')

        serializer = FlagSerializer(flags, many=True)
        return Response(serializer.data)


# ------------------------------------------------------------------ #
# PATCH /api/flags/{id}/  → reviewer updates flag status
# ------------------------------------------------------------------ #
class FlagDetailView(APIView):

    def patch(self, request, pk):
        # Try to find the flag — return 404 if it doesn't exist
        try:
            flag = Flag.objects.get(pk=pk)
        except Flag.DoesNotExist:
            return Response(
                {'error': 'Flag not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = FlagStatusUpdateSerializer(
            flag,
            data=request.data,
            partial=True        # PATCH = partial update, not full replace
        )

        if serializer.is_valid():
            # If reviewer marks it irrelevant, record the timestamp
            # This timestamp is what drives the suppression logic
            new_status = serializer.validated_data.get('status')
            if new_status == 'irrelevant':
                flag.reviewed_at = timezone.now()

            serializer.save()
            # Return the full flag so reviewer sees the updated state
            return Response(
                FlagSerializer(flag).data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    