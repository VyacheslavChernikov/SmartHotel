from django.db import models
import secrets

class Hotel(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    api_key = models.CharField(max_length=64, unique=True, default=secrets.token_hex(32))
    address = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
class Hotel(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    slug = models.SlugField(unique=True, verbose_name="Слаг")
    api_key = models.CharField(max_length=64, unique=True, default=secrets.token_hex(32), verbose_name="API ключ")
    address = models.CharField(max_length=255, blank=True, verbose_name="Адрес")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Отель"
        verbose_name_plural = "Отели"
