from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).exclude(
            event_type=Notification.EventType.MFA_OTP,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).exclude(
        event_type=Notification.EventType.MFA_OTP,
    ).update(is_read=True)
    return Response({'detail': 'All notifications marked as read.'})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_read(request, pk):
    try:
        notif = Notification.objects.get(id=pk, user=request.user)
        notif.is_read = True
        notif.save()
        return Response({'detail': 'Marked as read.'})
    except Notification.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)


class NotificationDestroyView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).exclude(
            event_type=Notification.EventType.MFA_OTP,
        )


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        pref, _ = NotificationPreference.objects.get_or_create(user=self.request.user)
        return pref
