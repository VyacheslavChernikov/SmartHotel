from django.db import models
from hotels.models import Hotel


class Room(models.Model):
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name="rooms",
        verbose_name="Отель"
    )
    room_number = models.CharField(max_length=50, verbose_name="Номер комнаты")
    room_type = models.CharField(max_length=255, verbose_name="Тип номера")
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена за ночь")
    is_available = models.BooleanField(default=True, verbose_name="Свободен")

    class Meta:
        verbose_name = "Номер"
        verbose_name_plural = "Номера"

    def __str__(self):
        return f"{self.room_number} ({self.hotel.name})"
