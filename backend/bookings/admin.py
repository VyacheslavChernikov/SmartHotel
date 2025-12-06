from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "hotel", "room", "guest_name", "date_from", "date_to", "is_confirmed")
    list_filter = ("hotel", "room", "is_confirmed")
    search_fields = ("guest_name", "guest_phone", "guest_email")
