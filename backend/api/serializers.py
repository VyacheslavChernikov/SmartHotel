from rest_framework import serializers
from hotels.models import Hotel
from rooms.models import Room
from bookings.models import Booking


class HotelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = ["id", "name", "slug", "address", "description"]


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "hotel", "room_number", "room_type", "price_per_night", "is_available"]


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "id",
            "hotel",
            "room",
            "guest_name",
            "guest_phone",
            "guest_email",
            "date_from",
            "date_to",
            "total_price",
            "is_confirmed",
        ]
