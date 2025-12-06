from django.urls import path
from .views import HotelListAPIView, RoomListAPIView, BookingCreateAPIView

urlpatterns = [
    path("hotels/", HotelListAPIView.as_view(), name="hotel-list"),
    path("rooms/", RoomListAPIView.as_view(), name="room-list"),
    path("booking/", BookingCreateAPIView.as_view(), name="booking-create"),
]
