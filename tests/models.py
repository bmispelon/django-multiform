from django.db import models


class Pizza(models.Model):
    name = models.CharField(max_length=50)
    restaurant = models.ManyToManyField('Restaurant')


class Restaurant(models.Model):
    name = models.CharField(max_length=50)


class Topping(models.Model):
    pizza = models.ForeignKey(Pizza)
    name = models.CharField(max_length=50)
