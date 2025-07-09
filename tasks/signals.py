# tasks/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Component, Order, OrderComponent, Profile

@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    """
    Lorsqu'un utilisateur est créé, ce signal crée automatiquement un Profile.
    Si l'utilisateur existait déjà, son Profile est simplement mis à jour.
    """
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()

@receiver(post_save, sender=Order)
def create_order_components(sender, instance, created, **kwargs):
    """
    Lorsqu'une commande est créée, ce signal crée automatiquement les composants associés.
    Il récupère les composants liés à l'article de code de la commande et les associe.
    """
    if created:
        # S'exécute uniquement lors de la création initiale de la commande
        components = Component.objects.filter(codeitem=instance.codeitem)
        for component in components:
            OrderComponent.objects.get_or_create(order=instance, component=component)

