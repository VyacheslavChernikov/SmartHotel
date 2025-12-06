from django.db import models
from hotels.models import Hotel
from rooms.models import Room

class Booking(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, verbose_name="Отель")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, verbose_name="Номер")

    guest_name = models.CharField(max_length=255, verbose_name="Имя гостя")
    guest_phone = models.CharField(max_length=50, verbose_name="Телефон")
    guest_email = models.EmailField(blank=True, null=True, verbose_name="Email")

    date_from = models.DateField(verbose_name="Дата заезда")
    date_to = models.DateField(verbose_name="Дата выезда")

    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Стоимость")
    is_confirmed = models.BooleanField(default=False, verbose_name="Подтверждено")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"

    def __str__(self):
        return f"Бронь #{self.id} — {self.guest_name}"
