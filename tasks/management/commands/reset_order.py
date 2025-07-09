from django.core.management.base import BaseCommand
from tasks.models import ComponentSerial, Defect, Order, OrderComponent, StepProgress


class Command(BaseCommand):
    help = "Resets an existing order by clearing progress, defects and setting it back to pending."

    def add_arguments(self, parser):
        parser.add_argument('order_id', type=int, help='Order ID to reset')

    def handle(self, *args, **kwargs):
        order_id = kwargs['order_id']

        try:
            order = Order.objects.get(order_id=order_id)
        except Order.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f"Order {order_id} does not exist."))
            return

        # Supprimer la progression
        StepProgress.objects.filter(order=order).delete()

        # Supprimer les défauts associés
        Defect.objects.filter(order=order).delete()

        # Supprimer les ComponentSerial associés
        ComponentSerial.objects.filter(order=order).delete()

        # Mettre à jour is_selected à False pour les composants associés
        OrderComponent.objects.filter(order=order).update(is_selected=False)
        
        # Réinitialiser l’état
        order.mo_status = 'pending'
        order.save()

        self.stdout.write(self.style.SUCCESS(
            f"Order {order_id} has been fully reset successfully."))

# python manage.py reset_order 1001
