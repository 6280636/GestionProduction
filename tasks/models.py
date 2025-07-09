from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext as _

# from django.utils.translation import gettext_lazy as _

# Create your models here.

class Profile(models.Model):
    """
    Étend le modèle User avec un numéro d'employé unique.
    Chaque utilisateur a un profil associé contenant son numéro d'employé.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("Utilisateur")  # Opcional, para que aparezca traducido en el admin
    )
    employee_number = models.PositiveIntegerField(
        unique=True,
        verbose_name=_("Numéro d'employé")
    )

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_number})"



class Order(models.Model):
    """
    Représente une commande de production.
    Contient les informations principales relatives à une commande.
    """
    order_id = models.PositiveIntegerField(
        unique=True,
        verbose_name=_("Identifiant de commande")
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_("Quantité commandée")
    )
    order_date = models.DateField(
        verbose_name=_("Date de la commande")
    )
    due_date = models.DateField(
        verbose_name=_("Date limite de livraison")
    )

    class MOStatus(models.TextChoices):
        PENDING = 'pending', _('En attente')
        SHIPPED = 'shipped', _('Expédiée')
        DELIVERED = 'delivered', _('Livrée')

    mo_status = models.CharField(
        max_length=20,
        choices=MOStatus.choices,
        verbose_name=_("Statut de la commande")
    )
    lot_number = models.CharField(
        max_length=5,
        verbose_name=_("Numéro de lot")
    )
    codeitem = models.ForeignKey(
        'CodeItem',
        on_delete=models.PROTECT,
        verbose_name=_("Item codé")
    )

    def __str__(self):
        return f"Commande {self.order_id}"   

class Procedure(models.Model):
    """
    Représente une procédure ou une instruction de travail.
    Contient les informations détaillées relatives à la procédure, 
    y compris les responsables et les dates de préparation, révision et approbation.
    """

    name = models.CharField(
        max_length=200,
        verbose_name=_("Nom de la procédure")  
    )
    description = models.TextField(
        verbose_name=_("Description détaillée de la procédure")
    )
    prepared_by = models.CharField(
        max_length=100,
        verbose_name=_("Nom de la personne qui a préparé la procédure")
    )
    prepared_date = models.DateField(
        verbose_name=_("Date de préparation")
    )
    reviewed_by = models.CharField(
        max_length=200,
        verbose_name=_("Nom de la personne qui a révisé la procédure")
    )
    review_date = models.DateField(
        verbose_name=_("Date de révision")
    )
    approved_by = models.CharField(
        max_length=200,
        verbose_name=_("Nom de la personne qui a approuvé la procédure")
    )
    approved_date = models.DateField(
        verbose_name=_("Date d'approbation")
    )
    procedure_number = models.CharField(
        max_length=50,
        verbose_name=_("Numéro d'identification de la procédure")
    )
    assembly_number = models.CharField(
        max_length=50,
        verbose_name=_("Numéro d'assemblage lié")
    )
    revision_number = models.CharField(
        max_length=20,
        verbose_name=_("Numéro de révision de la procédure")
    )

    def __str__(self):
        return f"{self.name} - {self.prepared_by}"
 
class CodeItem(models.Model):
    code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_("Code unique identifiant l'élément")  
    )
    procedure = models.ForeignKey(
        Procedure,
        on_delete=models.PROTECT,
        verbose_name=_("Lien vers la procédure associée, protection contre suppression")  
    )
    image = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Chemin ou URL vers une image générale du produit (optionnel)")  
    )
    def __str__(self):
        return self.code
                                                           

    
class Tool(models.Model):
    """
    Représente un outil utilisé dans une procédure.
    Chaque outil est lié à une procédure spécifique et peut avoir une image associée.
    """
    procedure = models.ForeignKey(
        Procedure,
        on_delete=models.CASCADE,
        related_name='tool_items',
        verbose_name=_("Liaison vers la procédure, suppression en cascade") 
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("Nom de l'outil")  
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Quantité nécessaire (par défaut 1)")  
    )
    image = models.ImageField(
        upload_to='tools/',
        blank=True,
        null=True,
        verbose_name=_("Image de l'outil stockée dans le dossier 'tools/'")  
    )

    def __str__(self):
        return self.name  
    
class Component(models.Model):
    """
    Représente un composant associé à un CodeItem.
    Chaque composant inclut des informations sur sa position visuelle et sa quantité requise.
    """

    codeitem = models.ForeignKey(
        CodeItem,
        on_delete=models.CASCADE,
        related_name='components',
        verbose_name=_("CodeItem associé")  
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("Nom du composant")  
    )
    item_id = models.CharField(
        max_length=50,
        verbose_name=_("Identifiant unique de l'élément")  
    )
    required_quantity = models.PositiveIntegerField(
        verbose_name=_("Quantité requise du composant")  
    )
    image = models.ImageField(
        upload_to='components/',
        blank=True,
        null=True,
        verbose_name=_("Image du composant")  
    )
    pos_x = models.PositiveIntegerField(
        default=0,
        help_text=_("px depuis le bord gauche"),  
        verbose_name=_("Position horizontale")   
    )
    pos_y = models.PositiveIntegerField(
        default=0,
        help_text=_("px depuis le bord supérieur"),  
        verbose_name=_("Position verticale")          
    )
    z_index = models.PositiveIntegerField(
        default=1,
        help_text=_("Ordre d'empilement"),  
        verbose_name=_("Ordre d'affichage (z-index)")  
    )

    def __str__(self):
        return f"{self.name} - {self.codeitem.code}"  

class WorkStep(models.Model):
    """
    Représente une étape individuelle dans une procédure de travail.
    Chaque étape est liée à une procédure spécifique et contient des informations détaillées 
    telles que le titre, la description, les unités nécessaires et les images associées.
    """

    procedure = models.ForeignKey(
        Procedure, 
        on_delete=models.CASCADE, 
        related_name='steps',        
    )
    step_number = models.PositiveIntegerField(
        
    )
    title = models.CharField(
        max_length=200,
        verbose_name=_("Titre de l'étape")
    )
    description = models.TextField(
        verbose_name=_("Description de l'étape")
    )
    units_required = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Unités nécessaires")
    )
    image = models.ImageField(
        upload_to='steps/',
        blank=True, 
        null=True,
        verbose_name=_("Image de l'étape")
    )
    thumbnail = models.ImageField(
        upload_to='thumbnails/',
        blank=True, 
        null=True,
        verbose_name=_("Miniature image")
    )
    video_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name=_("URL vidéo")
    )
    pdf_file = models.FileField(
        upload_to='pdfs/',
        blank=True, 
        null=True,
        verbose_name=_("Fichier PDF")
    )

    def __str__(self):
        return f"Step {self.step_number}: {self.title}"

    class Meta:
        ordering = ['step_number']
        verbose_name = _("Étape de travail")
        verbose_name_plural = _("Étapes de travail")

    

class WorkStepDefect(models.Model):
    """
    Enregistre les défauts identifiés à une étape spécifique d'une commande.
    Chaque défaut est lié à une commande et une étape de procédure, avec la quantité affectée,
    l'utilisateur qui a signalé le défaut et un horodatage automatique.
    """

    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE,
        verbose_name=_("Commande concernée")
    )
    step = models.ForeignKey(
        WorkStep, 
        on_delete=models.CASCADE,
        verbose_name=_("Étape de travail")
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_("Quantité défectueuse")
    )
    reported_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Signalé par")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date et heure de signalement")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes supplémentaires")
    )

    def __str__(self):
        return f"Défaut à l'étape {self.step.step_number} pour commande {self.order.order_id} (Qté: {self.quantity})"

    class Meta:
        verbose_name = _("Défaut d'étape de travail")
        verbose_name_plural = _("Défauts d'étapes de travail")
        ordering = ['-timestamp']


class Defect(models.Model):
    """
    Représente un défaut signalé lors d'une étape spécifique d'une commande.
    Contient des détails sur le type de défaut, le numéro de pièce, l'unité affectée,
    l'autorisation et les notifications associées.
    """

    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE,
        verbose_name=_("Commande liée")
    )
    step = models.ForeignKey(
        WorkStep, 
        on_delete=models.CASCADE,
        verbose_name=_("Étape du processus")
    )
    defect_type = models.CharField(
        max_length=100,
        verbose_name=_("Type de défaut")
    )
    part_number = models.CharField(
        max_length=100,
        verbose_name=_("Numéro de pièce")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes supplémentaires")
    )
    authorized_by = models.CharField(
        max_length=100,
        verbose_name=_("Autorisé par")
    )
    notify_email = models.EmailField(
        blank=True,
        verbose_name=_("Email de notification")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date et heure de déclaration")
    )
    unit_number = models.PositiveIntegerField(
        verbose_name=_("Numéro d’unité")
    )

    def __str__(self):
        return f"Défaut sur commande {self.order.order_id} - Étape {self.step.step_number}"

    class Meta:
        verbose_name = _("Défaut")
        verbose_name_plural = _("Défauts")
        ordering = ['-timestamp']


class StepProgress(models.Model):
    """
    Suit l'avancement d'une unité spécifique à travers les étapes d'une commande.
    Permet de savoir quelles étapes ont été complétées pour chaque unité de production.
    """

    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE,
        verbose_name=_("Commande concernée")
    )
    unit_number = models.PositiveIntegerField(
        verbose_name=_("Numéro de l’unité de production")
    )
    step = models.ForeignKey(
        WorkStep, 
        on_delete=models.CASCADE,
        verbose_name=_("Étape spécifique")
    )
    completed = models.BooleanField(
        default=False,
        verbose_name=_("Étape complétée")
    )
    completed_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name=_("Date et heure de complétion")
    )

    class Meta:
        unique_together = ('order', 'unit_number', 'step')
        ordering = ['unit_number', 'step__step_number']
        verbose_name = _("Progression de l'étape")
        verbose_name_plural = _("Progressions des étapes")

    def __str__(self):
        return f"Commande {self.order.order_id} - Unité {self.unit_number} - Étape {self.step.step_number}"

    
class OrderComponent(models.Model):
    """
    Lie une commande à ses composants spécifiques.
    Permet de suivre quels composants sont utilisés pour une commande donnée.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name=_("Commande")
    )
    component = models.ForeignKey(
        Component,
        on_delete=models.CASCADE,
        verbose_name=_("Composant")
    )
    is_selected = models.BooleanField(
        default=False,
        verbose_name=_("Sélectionné")
    )

    class Meta:
        unique_together = ('order', 'component')
        verbose_name = _("Composant de commande")
        verbose_name_plural = _("Composants de commande")

    def __str__(self):
        status = "Sélectionné" if self.is_selected else "Non sélectionné"
        return f"Commande {self.order.order_id} - Composant {self.component.name} ({status})"
    
class ComponentSerial(models.Model):
    order = models.ForeignKey(
        'Order',
        on_delete=models.CASCADE,
        verbose_name=_("Commande")
    )
    component = models.ForeignKey(
        'Component',
        on_delete=models.PROTECT,
        verbose_name=_("Composant lié")
    )
    unit_number = models.PositiveIntegerField(
        verbose_name=_("Unité de production")
    )
    serial_number = models.CharField(
        max_length=100,
        verbose_name=_("Numéro de série")
    )
    component_name = models.CharField(
        max_length=100,
        verbose_name=_("Nom du composant (copié)")
    )
    volt = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True)  
    gain = models.PositiveIntegerField(null=True, blank=True) 
     
    def __str__(self):
        return f"{self.serial_number} ({self.component_name})"




   
    



