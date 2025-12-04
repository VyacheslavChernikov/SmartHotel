from rest_framework import generics
from hotels.models import Hotel
from rooms.models import Room
from bookings.models import Booking
from .serializers import HotelSerializer, RoomSerializer, BookingSerializer


class HotelListAPIView(generics.ListAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer


class RoomListAPIView(generics.ListAPIView):
    serializer_class = RoomSerializer

    def get_queryset(self):
        """
        Возвращает только свободные комнаты.
        Возможна фильтрация по отелю: /api/rooms/?hotel=1
        """
        qs = Room.objects.filter(is_available=True)

        hotel_id = self.request.query_params.get("hotel")

        if hotel_id:
            qs = qs.filter(hotel_id=hotel_id)

        return qs


class BookingCreateAPIView(generics.CreateAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
