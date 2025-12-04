from django.contrib import admin
from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "room_type", "price_per_night", "hotel", "is_available")
    list_filter = ("hotel", "is_available")
    search_fields = ("room_number", "room_type")
