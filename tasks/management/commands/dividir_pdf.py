from django.core.management.base import BaseCommand
from PyPDF2 import PdfReader, PdfWriter

class Command(BaseCommand):
    help = "Divise un PDF local en plusieurs parties spécifiques"

    def handle(self, *args, **kwargs):
        chemin_pdf = "C:/Users/sotomayv/Desktop/99918-0008-01.pdf"
        lecteur = PdfReader(chemin_pdf)
        total_pages = len(lecteur.pages)
        self.stdout.write(f"Nombre total de pages dans le PDF: {total_pages}")

        # Définition des plages spécifiques (en indice base 1)
        plages = [
            (2, 3),
            (3, 5),
            (6, 7),
            (8, 12),
        ]

        for debut, fin in plages:
            ecrivain = PdfWriter()
            # Note: PyPDF2 utilise des indices de page basés sur 0
            for i in range(debut - 1, fin):
                if i < total_pages:
                    ecrivain.add_page(lecteur.pages[i])
                else:
                    self.stdout.write(self.style.WARNING(f"La page {i+1} dépasse le total de pages"))

            nom_fichier = f"partie_{debut}_a_{fin}.pdf"
            with open(nom_fichier, "wb") as f:
                ecrivain.write(f)

            self.stdout.write(f"Créé: {nom_fichier}")

        self.stdout.write(self.style.SUCCESS("Division terminée avec succès."))

#python manage.py dividir_pdf