from cProfile import Profile
from datetime import datetime, timezone
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.core.mail import send_mail
from djangocrud import settings
from .forms import DefectForm, EmployeeLoginForm
from .models import ComponentSerial, Defect, Order, OrderComponent, Procedure, Component, Profile, StepProgress, WorkStep, WorkStepDefect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.timezone import now
from django.contrib.auth import authenticate
from django.utils import timezone
from collections import Counter
from django.utils.translation import gettext as _
import can
import time
from .pcan_utils import get_bus, bus_lock
from django.views.decorators.csrf import csrf_exempt

def order_detail(request, order_id):
    """Affiche les détails d'une commande spécifique si la requête est GET."""

    if request.method == "GET":
        try:
            order = Order.objects.get(order_id=order_id)
            # Affiche la page de détails de la commande avec ses informations
            return render(request, 'order_detail.html', {
                'order': order,
            })
        except Order.DoesNotExist:
            # Si la commande n'existe pas, affiche un message d'erreur
            return render(request, 'order_detail.html', {
                'error': _('La commande ne existe pas.')  # ✅ Traduction avec _
            })


def order_search(request):
    """Gère la recherche d'une commande par son identifiant et affiche les résultats ou un message d'erreur."""

    order = None
    error = None

    # Si la requête est de type POST (soumission du formulaire)
    if request.method == 'POST':
        order_id = request.POST.get('orderId')
        if order_id:
            try:
                order = Order.objects.get(order_id=order_id)

                if order.mo_status == 'shipped':
                    return redirect('order_completed', order_id=order.order_id)

            except Order.DoesNotExist:
                error = _('La commande n’existe pas.')  # ✅ Message traduit

    # Affiche la page de détails de la commande (avec ou sans résultats)
    return render(request, 'order_detail.html', {
        'order': order,
        'error': error
    })


def verify_components(request, order_id):
    """Permet de vérifier et afficher les composants associés à une commande,
    en indiquant leur sélection, puis redirige vers la séquence de travail après validation."""

    order = get_object_or_404(Order, order_id=order_id)
    procedure = order.codeitem.procedure

    # Récupère les composants associés à l'article de la commande
    components = Component.objects.filter(codeitem=order.codeitem)

    # Pour chaque composant, vérifie s'il est déjà associé à la commande
    for component in components:
        try:
            oc = OrderComponent.objects.get(order=order, component=component)
            component.is_selected = oc.is_selected
        except OrderComponent.DoesNotExist:
            component.is_selected = False

    # Divise la liste des composants en deux parties pour l'affichage
    half = len(components) // 2
    components_first_half = components[:half]
    components_second_half = components[half:]

    if request.method == 'POST':
        # Redirige vers la séquence de travail après vérification (état à enregistrer si nécessaire)
        return redirect('work_sequence', order_id=order.order_id)

    # Affiche la page de vérification des composants avec toutes les données nécessaires
    return render(request, 'verify_components.html', {
        'order': order,
        'components': components,
        'procedure': procedure,
        'components_first_half': components_first_half,
        'components_second_half': components_second_half,
    })


@require_POST  # Assure que cette vue ne peut être appelée qu'avec une requête HTTP POST
def toggle_component(request, order_id, component_id):
    print(
        f"toggle_component appelé avec order_id={order_id}, component_id={component_id}")
    try:
        order = get_object_or_404(Order, order_id=order_id)
        component = get_object_or_404(Component, id=component_id)

        # Récupère la relation entre la commande et le composant (OrderComponent)
        order_component = get_object_or_404(
            OrderComponent, order=order, component=component)

        # Vérifie si le composant n'est pas encore sélectionné
        if not order_component.is_selected:
            # Marque le composant comme sélectionné et sauvegarde la modification
            order_component.is_selected = True
            order_component.save()
            print(_("Composant marqué comme sélectionné"))  # ✅ Texte traduit
            return JsonResponse({'status': 'success', 'is_selected': True})
        else:
            # ✅ Texte traduit
            print(_("Le composant était déjà sélectionné; pas de changement"))
            return JsonResponse({'status': 'no_change', 'is_selected': True})

    except Exception as e:
        print(f"{_('Erreur dans toggle_component')} : {e}")  # ✅ Texte traduit
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def procedure_detail(request, procedure_id):
    """Affiche les détails d'une procédure et d'une commande associée."""

    # Récupère la procédure demandée
    procedure = get_object_or_404(Procedure, id=procedure_id)

    # Cherche une commande associée à un codeitem lié à cette procédure
    order = Order.objects.filter(codeitem__procedure=procedure).first()

    # Récupère la section actuelle depuis les paramètres GET de l'URL ; 'section1' est utilisée par défaut
    current_section = request.GET.get('page', 'section1')

    # Si la section demandée est 'section2', on affiche un template différent
    if current_section == 'section2':
        return render(request, 'procedure_detail1.html', {
            'procedure': procedure,
            'order': order,
            'show_section2': True  # 🔁 plus clair et explicite
        })
    else:
        # Sinon, on affiche la vue par défaut
        return render(request, 'procedure_detail.html', {
            'procedure': procedure,
            'order': order,
            'show_section2': False
        })


def employee_login(request):
    """Gère la connexion d'un employé à partir de son numéro d'employé."""

    if request.method == 'POST':
        form = EmployeeLoginForm(request.POST)

        if form.is_valid():
            employee_number = form.cleaned_data['employee_number']
            try:
                profile = Profile.objects.get(employee_number=employee_number)
                user = profile.user
                login(request, user)
                return redirect('order_search')
            except Profile.DoesNotExist:
                if not form.errors.get('employee_number'):
                    form.add_error('employee_number', _(
                        "Le numéro d'employé est invalide."))  # ✅ Traduction
    else:
        form = EmployeeLoginForm()

    return render(request, 'employee_login.html', {'form': form})


def employee_logout(request):
    logout(request)
    return redirect('employee_login')


def work_sequence(request, order_id):
    """Affiche les étapes de travail d'une commande spécifique."""

    order = get_object_or_404(Order, order_id=order_id)
    procedure = order.codeitem.procedure
    steps = procedure.steps.all()

    # Crée un dictionnaire associant l'ID de chaque étape à son état d'avancement pour cette commande
    progress_map = {
        p.step_id: p for p in StepProgress.objects.filter(order=order)
    }

    # Prépare les données à passer au template
    context = {
        'order': order,
        'steps': steps,
        'progress_map': progress_map,
    }

    # Rend la page HTML avec les données du contexte
    return render(request, 'production/work_sequence.html', context)


def report_step_defect(request, order_id, step_id):
    """Gère le signalement d'un défaut pour une étape spécifique et envoie une notification par email."""

    order = get_object_or_404(Order, order_id=order_id)
    step = get_object_or_404(WorkStep, pk=step_id)
    components = Component.objects.filter(codeitem=order.codeitem)

    if request.method == 'POST':
        post_data = request.POST.copy()
        defect_type = post_data.get('defect_type')

        # Si le type de défaut est 'Autre', récupérer la valeur personnalisée
        if defect_type == 'Autre':
            autre_valeur = post_data.get('defect_type_autre', '').strip()
            if autre_valeur:
                post_data['defect_type'] = autre_valeur

        form = DefectForm(post_data)
        if form.is_valid():
            defect = form.save(commit=False)
            defect.order = order
            defect.step = step
            defect.timestamp = now()
            defect.authorized_by = request.user.username
            defect.notify_email = "victech701@gmail.com"

            # Attribution de l'unité en cours de traitement
            all_units = StepProgress.objects.filter(
                order=order).values_list('unit_number', flat=True).distinct()
            incomplete_units = [
                u for u in all_units if not is_unit_complete(order, u)]
            current_unit = min(incomplete_units, default=max(
                all_units) + 1 if all_units else 0)
            defect.unit_number = current_unit

            defect.save()

            recipient_list = [
                "victech701@gmail.com",
            ]

            try:
                send_mail(
                    subject=_("Défaut signalé - Ordre %(order_id)s, Étape %(step_number)s") % {
                        'order_id': order.order_id, 'step_number': step.step_number},
                    message=_(
                        "Un défaut a été signalé :\n\n"
                        "Ordre : %(order_id)s\n"
                        "Étape : %(step_number)s\n"
                        "Type de défaut : %(defect_type)s\n"
                        "Quantité : %(unit_number)s\n"
                        "Part number : %(part_number)s\n"
                        "Notes : %(notes)s\n"
                        "Signalé par : %(username)s\n"
                        "Date : %(timestamp)s\n"
                    ) % {
                        'order_id': order.order_id,
                        'step_number': step.step_number,
                        'defect_type': defect.defect_type,
                        'unit_number': defect.unit_number,
                        'part_number': defect.part_number,
                        'notes': defect.notes,
                        'username': request.user.username,
                        'timestamp': defect.timestamp,
                    },
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipient_list,
                    fail_silently=False,
                )
            except Exception as e:
                messages.warning(request, _(
                    "Défaut signalé, mais l'envoi de l'email a échoué : %(error)s") % {'error': e})

            messages.success(request, _("Défaut signalé avec succès."))
            return redirect('work_step_view', order_id=order_id, step_number=step.step_number)

    else:
        form = DefectForm()

    return render(request, 'production/defect_form.html', {
        'form': form,
        'order': order,
        'step': step,
        'components': components,
        'now': datetime.now().strftime('%Y-%m-%d'),
    })


def work_step_view(request, order_id, step_number):
    """Affiche les détails de une étape de travail pour une commande, gère la progression par unité, les défauts et l'état d'avancement."""

    order = get_object_or_404(Order, order_id=order_id)
    procedure = order.codeitem.procedure
    combined_serial = request.session.pop('combined_serial', '')
    # Obtenir toutes les étapes de la procédure ordonnées par numéro d'étape
    steps = WorkStep.objects.filter(
        procedure=procedure).order_by('step_number')
    # Obtenir l'étape courante selon le numéro d'étape fourni
    current_step = steps.get(step_number=step_number)

    # Guarder le pas de la session
    request.session["last_step_number"] = step_number

    # Obtenir toutes les unités qui ont été traitées
    # Obtenir toutes les unités avec défauts directement
    defective_units = Defect.objects.filter(
        order=order).values_list('unit_number', flat=True).distinct()
    defective_quantity = defective_units.count()  # Quantité d'unités défectueuses
    # Convertir en ensemble pour opérations rapides
    defective_units = set(defective_units)

    # Obtenir toutes les unités qui ont eu des étapes OU des défauts
    step_units = set(StepProgress.objects.filter(
        order=order).values_list('unit_number', flat=True))
    # Unités avec progression ou défauts
    all_units = step_units.union(defective_units)
    distinct_existing_units = all_units

    # Unités terminées (seulement si toutes les étapes terminées sans défaut)
    clean_completed_units = [
        unit for unit in all_units if is_unit_fully_clean(order, unit)]

    # Nombre d'unités terminées et propres (sans défauts)
    completed_units_count = len(clean_completed_units)

    # Unités non défectueuses qui ont passé les étapes et sont marquées comme complétées
    all_non_defective_units = StepProgress.objects.filter(
        order=order,
        completed=True
    ).exclude(unit_number__in=defective_units).values_list('unit_number', flat=True)

    # Compter combien de fois chaque unité non défectueuse complétée apparaît
    unit_counts = Counter(all_non_defective_units)
    # Compter les unités incomplètes qui ne sont pas dans les unités propres terminées
    incomplete_units_count = sum(
        1 for unit in unit_counts if unit not in clean_completed_units)

    # Déterminer l'unité actuelle sur laquelle travailler
    if not distinct_existing_units:
        current_unit = 0  # Si aucune unité, commencer à 0
    else:
        # Chercher unités incomplètes qui ne sont pas défectueuses
        incomplete_units = [
            u for u in distinct_existing_units
            if not is_unit_complete(order, u) and not is_unit_defective(order, u)
        ]
        # Choisir la plus petite unité incomplète, ou la suivante après la plus grande si aucune
        current_unit = min(incomplete_units, default=max(
            distinct_existing_units) + 1)

    # Vérifier si la somme des unités terminées et défectueuses a atteint la quantité commandée
    bloquear_botones = (completed_units_count +
                        defective_quantity) >= order.quantity

    # Créer la progression pour chaque étape de l'unité actuelle si les boutons ne sont pas bloqués
    if not bloquear_botones:
        for step in steps:
            StepProgress.objects.get_or_create(
                order=order, unit_number=current_unit, step=step)    
    # Obtenir la progression de l'unité actuelle
    step_progress = StepProgress.objects.filter(
        order=order, unit_number=current_unit)
    # Créer un dictionnaire avec l'état de complétion par étape
    completed_steps = {p.step.id: p.completed for p in step_progress}

    # Vérifier si l'on peut enregistrer l'étape actuelle (dépend de l'étape précédente)
    prev_step = steps.filter(step_number=current_step.step_number - 1).first()
    can_register = True
    if prev_step:
        # Obtenir la progression de l'étape précédente pour l'unité actuelle
        prev_progress = StepProgress.objects.filter(
            order=order,
            unit_number=current_unit,
            step=prev_step
        ).first()
        # Vérifier s'il y a des défauts à l'étape précédente
        defecto_prev = Defect.objects.filter(
            order=order,
            unit_number=current_unit,
            step=prev_step
        ).exists()
        # Autoriser l'enregistrement si l'étape précédente est terminée ou a un défaut
        can_register = (
            prev_progress and prev_progress.completed) or defecto_prev

    # Rendu de la vue avec toutes les données nécessaires
    return render(request, 'production/work_step.html', {
        'order': order,
        'step': current_step,
        'all_steps': steps,
        'progress': step_progress,
        'completed_steps': completed_steps,
        'current_unit': current_unit,
        'total_units': order.quantity,
        'defect_count': defective_quantity,
        'completed_units_count': completed_units_count,
        'incomplete_units_count': incomplete_units_count,
        'can_register': can_register and not bloquear_botones,
        'bloquear_botones': bloquear_botones,
        'total_units_reported': completed_units_count + defective_quantity,
        'combined_serial': combined_serial,
    })


def is_unit_defective(order, unit_number):
    # Vérifie si l'unité donnée a au moins un défaut signalé
    return Defect.objects.filter(order=order, unit_number=unit_number).exists()


def is_unit_fully_clean(order, unit_number):
    # Nombre total d'étapes dans la procédure liée à la commande
    total_steps = WorkStep.objects.filter(
        procedure=order.codeitem.procedure).count()

    # Vérifie si l'unité a des défauts signalés
    has_defects = Defect.objects.filter(
        order=order,
        unit_number=unit_number
    ).exists()

    if has_defects:
        return False

    # Récupère les IDs des étapes complétées pour cette unité
    completed_step_ids = StepProgress.objects.filter(
        order=order,
        unit_number=unit_number,
        completed=True
    ).values_list('step_id', flat=True)

    # Retourne True si le nombre d'étapes complétées correspond au total d'étapes
    return len(set(completed_step_ids)) == total_steps


def is_unit_complete(order, unit_number):
    """
    Vérifie si une unité est complète. Retourne True si le nombre total d'étapes (complétées ou avec défaut)
    correspond au nombre total d'étapes requises par la procédure.
    """

    # Obtenir le nombre total d'étapes dans la procédure associée à la commande
    total_steps = WorkStep.objects.filter(
        procedure=order.codeitem.procedure).count()

    # Récupérer les IDs des étapes complétées pour cette unité
    completed_step_ids = StepProgress.objects.filter(
        order=order,
        unit_number=unit_number,
        completed=True
    ).values_list('step_id', flat=True)

    # Récupérer les IDs des étapes où des défauts ont été signalés pour cette unité
    defect_step_ids = Defect.objects.filter(
        order=order,
        unit_number=unit_number
    ).values_list('step_id', flat=True)

    # Combiner les étapes complétées et les étapes avec défauts pour obtenir les étapes traitées
    unique_step_ids = set(completed_step_ids).union(defect_step_ids)

    # L'unité est complète si toutes les étapes ont été traitées (complétées ou avec défaut)
    return len(unique_step_ids) == total_steps


def update_step_progress(request, order_id, step_id):
    """Met à jour la progression d'une étape de travail pour une commande et une unité donnée.
    Gère l'enregistrement de l'étape ou la création d'un défaut selon l'entrée,
    et redirige selon l'état d'avancement de la commande."""
    order = get_object_or_404(Order, order_id=order_id)
    step = get_object_or_404(WorkStep, id=step_id)


    if request.method == 'POST':
       
        # Récupérer toutes les unités déjà traitées pour cette commande
        all_units = set(StepProgress.objects.filter(
            order=order).values_list('unit_number', flat=True))
        # Garder uniquement les unités valides (sans défauts, ici on prend toutes pour simplifier)
        valid_units = list(all_units)
        # Identifier les unités incomplètes parmi celles valides
        incomplete_units = [
            u for u in valid_units if not is_unit_complete(order, u)]

        # Choisir la première unité incomplète ou une nouvelle unité si toutes sont complètes
        if incomplete_units:
            current_unit = min(incomplete_units)
        else:
            current_unit = max(valid_units, default=-1) + 1

        # Vérifier si on dépasse la quantité commandée
        if current_unit > order.quantity:
            return redirect('work_step_view', order_id=order.order_id, step_number=step.step_number)

        # Vérifier l'existence d'un défaut pour cette étape et unité
        has_defect = Defect.objects.filter(
            order=order, step=step, unit_number=current_unit).exists()

        # Récupérer le signalement de défaut depuis la requête POST
        defect_flag = request.POST.get('defect', 'false').lower() == 'true'

        if defect_flag and not has_defect:
            # Créer un nouveau défaut signalé pour cette étape et unité
            Defect.objects.create(
                order=order, step=step, unit_number=current_unit, description=_("Défaut signalé"))
        else:
            # Marquer l'étape comme complétée si pas de défaut
            progress_entry, _ = StepProgress.objects.get_or_create(
                order=order, step=step, unit_number=current_unit)
            progress_entry.completed = True
            progress_entry.completed_at = now()
            progress_entry.save()

        ###############################
      # ✅ Si on est à l'étape 2 et que le numéro de procédure correspond, enregistrer les numéros de série
            if step.step_number == 2 and order.codeitem.procedure.procedure_number == "99918-0008-01":
                code_bobine = request.POST.get("hidden1", "").strip()
                code_rtd = request.POST.get("hidden2", "").strip()
                serial_values = []

                for code in [code_bobine, code_rtd]:
                    if code.startswith("N"):
                        # Nom du composant pour un assemblage RTD
                        composant_nom = "Assemblage RTD+Flange rod support"
                    elif code.startswith("B"):
                        # Nom du composant pour une bobine
                        composant_nom = "Bobine"
                    else:
                        continue  # Ignore si le code ne commence ni par N ni par B

                    try:
                        # Recherche du composant correspondant dans le CodeItem
                        component = Component.objects.get(
                            name__iexact=composant_nom, codeitem=order.codeitem)
                    except Component.DoesNotExist:
                        messages.warning(request,  _("⚠️ Composant '%(composant)s' introuvable dans ce CodeItem.") % {
                                        'composant': composant_nom})
                        continue

                    # Création et enregistrement de l'entrée dans ComponentSerial
                    ComponentSerial.objects.create(
                        order=order,
                        component=component,
                        unit_number=current_unit,
                        serial_number=code,
                        component_name=component.name,
                    )
                    # Ajouter à la liste pour la génération du QR
                    serial_values.append(f"{composant_nom}: {code}")               

                # Générer la chaîne combinée à passer à la vue pour impression
                if serial_values:
                    messages.success(request, "✅ Numéros de série enregistrés avec succès.")
                    combined_serial = " | ".join(serial_values)
                    request.session['combined_serial'] = combined_serial  # Guarda para imprimir QR
        #################################
        # ✅ Si on est à l’étape 4 et que le numéro de procédure correspond, enregistrer les infos du Board
            # if step.step_number == 4 and order.codeitem.procedure.procedure_number == "99918-0008-01":
            #     code_board = request.POST.get("board", "").strip()
            #     volt = request.POST.get("volt", "").strip()
            #     gain = request.POST.get("gain", "").strip()

            #     if not code_board.startswith("L"):
            #         messages.error(request, "⚠️ Le code du Board doit commencer par 'L'.")
            #         return redirect(request.path)
            #     try:
            #         volt = float(volt)
            #     except ValueError:
            #         messages.error(request, "⚠️ Volt doit être un nombre valide (ex: 3.1).")
            #         return redirect(request.path)

            #     try:
            #         gain = int(gain)
            #         if not (0 <= gain <= 80):
            #             messages.error(request, "⚠️ Le gain doit être un nombre entre 0 et 80.")
            #             return redirect(request.path)
            #     except ValueError:
            #         messages.error(request, "⚠️ Le gain doit être un entier valide.")
            #         return redirect(request.path)

            #     composant_nom = "PCB epoxy"

            #     try:
            #         # Recherche du composant correspondant
            #         component = Component.objects.get(name__iexact=composant_nom, codeitem=order.codeitem)
            #     except Component.DoesNotExist:
            #         messages.warning(request, _("⚠️ Composant '%(composant)s' introuvable dans ce CodeItem.") % {
            #             'composant': composant_nom})
            #         return redirect(request.path)

            #     # Enregistrement dans ComponentSerial 
            #     ComponentSerial.objects.create(
            #         order=order,
            #         component=component,
            #         unit_number=current_unit,
            #         serial_number=code_board,
            #         component_name=component.name,
            #         volt=volt,
            #         gain=gain,
            #     )

            #     messages.success(request, "✅ Données de Board enregistrées avec succès.")
            #     return redirect(request.path)

        #################################
        

        # Compter le nombre total d'étapes du procédé
        total_steps = WorkStep.objects.filter(procedure=step.procedure).count()

        # Obtenir la liste des étapes complétées pour cette unité
        completed_step_ids = StepProgress.objects.filter(
            order=order,
            unit_number=current_unit,
            completed=True
        ).values_list('step_id', flat=True)

        # Obtenir la liste des étapes avec défauts pour cette unité
        defect_step_ids = Defect.objects.filter(
            order=order,
            unit_number=current_unit
        ).values_list('step_id', flat=True)

        # Union des étapes complétées et des étapes avec défauts
        unique_step_ids = set(completed_step_ids).union(defect_step_ids)

        # Vérifier si toutes les étapes sont traitées (complétées ou avec défaut)
        unit_completed = len(unique_step_ids) == total_steps

        # Vérifier si on est à la dernière étape du procédé
        last_step = not WorkStep.objects.filter(
            procedure=step.procedure,
            step_number__gt=step.step_number
        ).exists()

        # Vérifier si on est à la dernière unité de la commande
        is_last_unit = current_unit + 1 == order.quantity

        # Si l'unité est terminée, passer à la suivante ou marquer la commande comme expédiée
        if unit_completed:
            if is_last_unit:
                order.mo_status = 'shipped'
                order.save()
                return redirect('order_completed', order_id=order.order_id)
            else:
                return redirect('work_step_view', order_id=order.order_id, step_number=1)

        # Sinon, avancer à l'étape suivante dans la même unité si ce n'est pas la dernière étape
        if not last_step:
            return redirect('work_step_view', order_id=order.order_id, step_number=step.step_number + 1)
        else:
            # Si dernière étape mais unité pas complète, revenir au début du procédé
            return redirect('work_step_view', order_id=order.order_id, step_number=1)

    # Redirection par défaut si la méthode n'est pas POST
    return redirect('work_step_view', order_id=order_id, step_number=step.step_number)


def order_completed(request, order_id):
    """Affiche le résumé de la commande une fois terminée."""

    order = get_object_or_404(Order, order_id=order_id)

    # Récupérer les numéros d'unités qui ont des défauts dans la commande
    defective_units = set(
        Defect.objects.filter(order=order).values_list(
            'unit_number', flat=True).distinct()
    )
    defective_quantity = len(defective_units)

    # Obtenir les unités qui ont déjà progressé dans le processus de fabrication
    step_units = set(
        StepProgress.objects.filter(order=order).values_list(
            'unit_number', flat=True)
    )

    # Fusionner les unités avec défauts et celles ayant des progrès pour avoir toutes les unités concernées
    all_units = step_units.union(defective_units)

    # Filtrer les unités terminées correctement sans aucun défaut
    clean_completed_units = [
        unit for unit in all_units if is_unit_fully_clean(order, unit)
    ]
    completed_count = len(clean_completed_units)

    # Vérifier si la quantité terminée atteint ou dépasse la quantité demandée dans la commande
    work_completed = (completed_count >= order.quantity)

    # Temps écoulé non calculé ici, peut être ajouté plus tard
    elapsed_time = "Non défini"
    usuario = request.user

    context = {
        'order': order,
        'completed_units': completed_count,
        'defect_count': defective_quantity,
        'user': usuario,
        'date': timezone.now(),
        'elapsed_time': elapsed_time,
        'travail_termine': work_completed,
    }
    return render(request, 'production/order_completed.html', context)


def reopen_order(request, order_id):
    """Permet à un superviseur authentifié de rouvrir une commande terminée,
    en réinitialisant les défauts."""

    if request.method == "POST":
        username = request.POST.get("supervisor_username")
        password = request.POST.get("supervisor_password")

        user = authenticate(username=username, password=password)

        if user and user.is_staff:
            order = get_object_or_404(Order, order_id=order_id)
            # Marquer la commande comme non terminée pour la rouvrir
            order.is_completed = False
            order.save()

            # Récupérer les unités avec des défauts avant suppression
            defective_units = list(
                Defect.objects.filter(order=order).values_list(
                    'unit_number', flat=True).distinct()
            )

            # Supprimer tous les défauts associés à la commande
            Defect.objects.filter(order=order).delete()
            # Supprimer les progrès des unités défectueuses pour réinitialiser leur état
            StepProgress.objects.filter(
                order=order, unit_number__in=defective_units).delete()

            # Recréer les étapes de travail vierges pour chaque unité défectueuse
            steps = WorkStep.objects.filter(
                procedure=order.codeitem.procedure).order_by('step_number')
            for unit in defective_units:
                for step in steps:
                    StepProgress.objects.get_or_create(
                        order=order, unit_number=unit, step=step)

            messages.success(
                request, _("La commande a été rouverte avec succès."))
            return redirect('work_step_view', order_id=order.order_id, step_number=1)
        else:
            # Si l'authentification échoue, avertir l'utilisateur
            messages.warning(request, _("Identifiants du superviseur invalides."))
            return redirect('work_step_view', order_id=order_id, step_number=1)

    # Redirection par défaut pour les requêtes non POST
    return redirect('work_step_view', order_id=order_id, step_number=1)


def change_order_quantity(request, order_id):
    """Permet à un administrateur authentifié de modifier la quantité d'une commande."""

    if request.method == "POST":
        # Récupérer les identifiants administrateur et la nouvelle quantité depuis le formulaire
        username = request.POST.get("admin_username")
        password = request.POST.get("admin_password")
        new_quantity = request.POST.get("new_quantity")

        user = authenticate(username=username, password=password)

        if user is not None and user.is_staff:
            order = get_object_or_404(Order, order_id=order_id)

            try:
                # Convertir la quantité en entier et vérifier qu'elle est positive
                new_quantity_int = int(new_quantity)
                if new_quantity_int < 0:
                    messages.error(
                        request, _("La quantité doit être un nombre positif."))
                else:
                    # Mettre à jour la quantité de la commande et enregistrer
                    order.quantity = new_quantity_int
                    order.save()
                    messages.success(request, _("Quantité modifiée avec succès."))
            except ValueError:
                # Gérer le cas où la conversion en entier échoue
                messages.error(request, _("Quantité invalide."))

        else:
            # Message d'erreur si l'authentification échoue ou utilisateur non admin
            messages.error(request, _("Identifiants admin incorrects."))

    # Rediriger vers la page précédente après traitement du formulaire
    return redirect(request.META.get('HTTP_REFERER', '/'))
   
# ========================================
# Lecture du Volt et Gain depuis PCAN (Ajax)
# ========================================
def read_pcan(request, order_id, step_number):
    """
    Vue Ajax pour lire Gain, Volt et ajuster automatiquement le gain.
    Les actions sont affichées dans le terminal pour debug.
    """
    # Configuratión
    PASSWORD = [0x23, 0x02, 0x23, 0x01, 0x00, 0x5F, 0x37, 0x00]
    VOLT_TARGET = 3.26
    VOLT_TOL = 0.01
    VOLT_PER_GAIN = 0.009
    WAIT_TIME = 30
    MAX_GAIN = 255
    MIN_GAIN = 0

    bus = can.interface.Bus(interface='pcan', channel='PCAN_USBBUS1', bitrate=50000)

    try:
        # ---------------- Password -----------------
        print("📤 Envoi d'une demande de mot de passe...", flush=True)
        msg_pwd_req = can.Message(arbitration_id=0x601, is_extended_id=False,
                                  data=[0x43, 0x02, 0x23, 0x01, 0x00, 0x00, 0x00, 0x00])
        bus.send(msg_pwd_req)

        start = time.time()
        while time.time() - start < 3:
            msg = bus.recv(timeout=0.5)
            if msg and msg.arbitration_id == 0x581:
                print(f"📥 Réponse reçue: {msg.data}", flush=True)
                break

        msg_pwd_write = can.Message(arbitration_id=0x601, is_extended_id=False, data=PASSWORD)
        bus.send(msg_pwd_write)
        print(f"📤 Mot de passe envoyé: {[hex(b) for b in PASSWORD]}", flush=True)
        time.sleep(0.3)

        # ---------------- Réglage automatique du gain -----------------
        gain = None
        volt = None
        while True:
            # Lire Gain
            msg_gain = can.Message(arbitration_id=0x601, is_extended_id=False,
                                   data=[0x4F, 0x30, 0x21, 0x03, 0x00, 0x00, 0x00, 0x00])
            bus.send(msg_gain)
            print("📤 Demande de gain envoyée", flush=True)

            start = time.time()
            gain_actual = None
            while time.time() - start < 3:
                msg = bus.recv(timeout=0.5)
                if msg and msg.arbitration_id == 0x581 and msg.data[0] == 0x4F:
                    gain_actual = msg.data[4]
                    print(f"📥 Gain: {gain_actual}", flush=True)
                    break
            if gain_actual is None:
                print("⚠️ Impossible de lire Gain", flush=True)
                return JsonResponse({'error': 'Impossible de lire Gain'}, status=500)

            # Lire Voltage
            msg_volt = can.Message(arbitration_id=0x601, is_extended_id=False,
                                   data=[0x43, 0x20, 0x22, 0x02, 0x00, 0x00, 0x00, 0x00])
            bus.send(msg_volt)
            print("📤 Demande de volt envoyée", flush=True)

            start = time.time()
            raw_volt = None
            volt_actual = None
            while time.time() - start < 5:
                msg = bus.recv(timeout=0.5)
                if msg and msg.arbitration_id == 0x581:
                    raw_volt = msg.data[4] | (msg.data[5] << 8)
                    volt_actual = raw_volt * 0.001
                    print(f"📥 Voltage: {volt_actual:.3f} V (RAW={raw_volt})", flush=True)
                    break
            if volt_actual is None:
                print("⚠️ Impossible de lire voltage", flush=True)
                return JsonResponse({'error': 'Impossible de lire voltage'}, status=500)

            # Évaluer si cela est dans la tolérance
            diff = VOLT_TARGET - volt_actual
            if abs(diff) <= VOLT_TOL:
                gain = gain_actual
                volt = volt_actual
                print(f"✅ Volt dans limites de tolérance: {volt_actual:.3f} V", flush=True)
                break

            # Calculer et écrire un nouveau gain
            steps = round(diff / VOLT_PER_GAIN)
            nuevo_gain = gain_actual + steps
            nuevo_gain = max(MIN_GAIN, min(MAX_GAIN, nuevo_gain))
            msg_gain_write = can.Message(arbitration_id=0x601, is_extended_id=False,
                                         data=[0x2F, 0x30, 0x21, 0x03, nuevo_gain & 0xFF, 0x00, 0x00, 0x00])
            bus.send(msg_gain_write)
            print(f"🔹 Réglage du gain de {gain_actual} a {nuevo_gain} (steps={steps})", flush=True)
            print(f"⏱ En attente {WAIT_TIME}s stabiliser...", flush=True)
            time.sleep(WAIT_TIME)

        # ---------------- Lire temperature -----------------
        msg_temp = can.Message(arbitration_id=0x601, is_extended_id=False,
                               data=[0x43, 0x00, 0x22, 0x03, 0x00, 0x00, 0x00, 0x00])
        bus.send(msg_temp)
        print("📤 Demande de température envoyée", flush=True)
        start = time.time()
        temp = None
        while time.time() - start < 5:
            msg = bus.recv(timeout=0.5)
            if msg and msg.arbitration_id == 0x581:
                raw_temp = msg.data[4] | (msg.data[5] << 8)
                temp = raw_temp * 0.001
                print(f"📥 Temperature: {temp:.1f} °C (RAW={raw_temp})", flush=True)
                break

        return JsonResponse({
            'gain': gain,
            'volt': round(volt, 3) if volt is not None else None,
            'temperature': round(temp, 1) if temp is not None else None
        })

    except Exception as e:
        print(f"❌ Error: {e}", flush=True)
        return JsonResponse({'error': str(e)}, status=500)

    finally:
        bus.shutdown()
        print("✅ Bus PCAN fermé", flush=True)

# ========================================
# Lecture simple du Volt, Gain et Temp
# ========================================
def read_pcan_values(request, order_id, step_number):
    """
    Vista Ajax para leer Gain, Volt, Temp, Board de la sonda PCAN.
    Mejor manejo: flush del buffer, matching exacto de respuesta, retries y delays.
    """
    try:
        with bus_lock:
            bus = get_bus()
            print("✅ Bus abierto para lectura inicial", flush=True)

            time.sleep(1.0)  # pequeño wait para estabilizar

            # ---- helper: vaciar buffer de mensajes pendientes ----
            def flush_incoming():
                # llamar varias veces con timeout muy pequeño hasta que no haya mensajes
                while True:
                    msg = bus.recv(timeout=0.001)
                    if not msg:
                        break
                    print(f"🧹 Flushed mensaje previo: ID={hex(msg.arbitration_id)}, data={msg.data}", flush=True)

            # ---- helper mejorado: enviar y esperar con matching exacto ----
            def send_and_wait(msg, match_prefix: bytes, parse_fn, retries=20, delay=0.8, timeout=0.8):
                """
                match_prefix: bytes a comparar con los primeros bytes de la respuesta (p.ej. b'\\x43\\x03\\x20\\x01')
                parse_fn: función que recibe el msg y devuelve el valor o None
                """
                for attempt in range(1, retries + 1):
                    flush_incoming()
                    bus.send(msg)
                    print(f"📤 Enviado (intento {attempt}): {msg.data}", flush=True)
                    start = time.time()
                    while time.time() - start < (timeout * 4):  # ventana total para esperar respuestas
                        resp = bus.recv(timeout=timeout)
                        if not resp:
                            continue
                        print(f"📥 Recibido: ID={hex(resp.arbitration_id)}, data={resp.data}", flush=True)

                        # comprobar arbitration id
                        if resp.arbitration_id != 0x581:
                            print("   -> Ignorado: arbitration_id distinto", flush=True)
                            continue

                        # comprobar prefix de datos si se indicó
                        data_bytes = bytes(resp.data)  # convertir para slicing
                        if match_prefix and not data_bytes.startswith(match_prefix):
                            print(f"   -> Ignorado: prefix no coincide {data_bytes[:len(match_prefix)]} != {match_prefix}", flush=True)
                            continue

                        # parsear
                        val = parse_fn(resp)
                        if val is not None:
                            print(f"   -> Parsed OK: {val}", flush=True)
                            return val

                    print(f"⏱️ Intento {attempt} no obtuvo respuesta válida, esperando {delay}s y reintentando...", flush=True)
                    time.sleep(delay)

                print("❌ Timeout total: no se obtuvo respuesta válida tras reintentos", flush=True)
                return None

            # --- Lot (esperamos respuesta con prefix C 0x03 0x20 0x01) ---
            lot_prefix = bytes([0x43, 0x03, 0x20, 0x01])
            lot_number = send_and_wait(
                can.Message(arbitration_id=0x601, is_extended_id=False,
                            data=[0x43, 0x03, 0x20, 0x01, 0, 0, 0, 0]),
                match_prefix=lot_prefix,
                parse_fn=lambda m: int(m.data[4]) if len(m.data) >= 5 else None,
                retries=20, delay=1, timeout=1
            )

            # pequeño delay antes de la siguiente petición (ayuda con sondas lentas)
            time.sleep(0.5)

            # --- Serial Board (prefix C 0x04 0x20 0x01) ---
            serial_prefix = bytes([0x43, 0x04, 0x20, 0x01])
            serial_board = send_and_wait(
                can.Message(arbitration_id=0x601, is_extended_id=False,
                            data=[0x43, 0x04, 0x20, 0x01, 0, 0, 0, 0]),
                match_prefix=serial_prefix,
                parse_fn=lambda m: (m.data[4] | (m.data[5] << 8)) if len(m.data) >= 6 else None,
                retries=20, delay=1, timeout=1
            )

            board_string = f"L{lot_number}-{serial_board}" if (lot_number is not None and serial_board is not None) else ""

            # ---- Gain (prefix 0x4F 0x30 0x21 0x03) ----
            gain_prefix = bytes([0x4F, 0x30, 0x21, 0x03])
            gain = send_and_wait(
                can.Message(arbitration_id=0x601, is_extended_id=False,
                            data=[0x4F, 0x30, 0x21, 0x03, 0, 0, 0, 0]),
                match_prefix=gain_prefix,
                parse_fn=lambda m: int(m.data[4]) if len(m.data) >= 5 else None,
                retries=20, delay=0.3, timeout=0.4
            )

            # ---- Volt ----
            volt_prefix = bytes([0x43, 0x20, 0x22, 0x02])
            volt = send_and_wait(
                can.Message(arbitration_id=0x601, is_extended_id=False,
                            data=[0x43, 0x20, 0x22, 0x02, 0, 0, 0, 0]),
                match_prefix=volt_prefix,
                parse_fn=lambda m: round((m.data[4] | (m.data[5] << 8)) * 0.001, 3) if len(m.data) >= 6 else None,
                retries=20, delay=0.2, timeout=0.4
            )

            # ---- Temp ----
            temp_prefix = bytes([0x43, 0x00, 0x22, 0x03])
            temp = send_and_wait(
                can.Message(arbitration_id=0x601, is_extended_id=False,
                            data=[0x43, 0x00, 0x22, 0x03, 0, 0, 0, 0]),
                match_prefix=temp_prefix,
                parse_fn=lambda m: round((m.data[4] | (m.data[5] << 8)) * 0.001, 1) if len(m.data) >= 6 else None,
                retries=20, delay=0.2, timeout=0.4
            )

            print(f"🔚 Resultado: board={board_string}, gain={gain}, volt={volt}, temp={temp}", flush=True)

            return JsonResponse({
                "gain": gain,
                "volt": volt,
                "temperature": temp,
                "board": board_string
            })

    except Exception as e:
        print(f"❌ Error en read_pcan_values: {e}", flush=True)
        return JsonResponse({"error": str(e)}, status=500)

# ========================================
# Mise a jour chaque second
# ========================================
def read_pcan_live(request):
    """
    Lee voltaje y temperatura en vivo cada 1-2 segundos.
    No reinicializa el bus, solo consulta los valores actuales.
    """
    try:
        with bus_lock:
            bus = get_bus()
            print("📡 Actualización en vivo...")

            def send_and_wait(msg, parse_fn, timeout=0.5):
                bus.send(msg)
                start = time.time()
                while time.time() - start < 1.0:
                    resp = bus.recv(timeout=timeout)
                    if resp:
                        parsed = parse_fn(resp)
                        if parsed is not None:
                            return parsed
                return None

            # 🔹 Voltaje (0x20, 0x22, 0x02)
            volt = send_and_wait(
                can.Message(arbitration_id=0x601, is_extended_id=False,
                            data=[0x43, 0x20, 0x22, 0x02, 0, 0, 0, 0]),
                lambda m: round((m.data[4] | (m.data[5] << 8)) * 0.001, 3)
                if m.arbitration_id == 0x581 and len(m.data) >= 6 else None
            )

            # 🔹 Temperatura (0x00, 0x22, 0x03)
            temp = send_and_wait(
                can.Message(arbitration_id=0x601, is_extended_id=False,
                            data=[0x43, 0x00, 0x22, 0x03, 0, 0, 0, 0]),
                lambda m: round((m.data[4] | (m.data[5] << 8)) * 0.001, 1)
                if m.arbitration_id == 0x581 and len(m.data) >= 6 else None
            )

            return JsonResponse({
                "volt": volt,
                "temperature": temp
            })

    except Exception as e:
        print(f"❌ Error en lectura en vivo: {e}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def close_pcan_bus(request):
    """
    Cierra el bus PCAN manualmente (llamado desde el frontend cuando el usuario
    sale de la página del paso 4).
    """
    try:
        shutdown_bus()
        return JsonResponse({"status": "ok", "message": "Bus cerrado manualmente"})
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)})

   

