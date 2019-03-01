from django.core.management.base import BaseCommand

from topobank.users.models import User
from topobank.manager.models import Surface, Topography
from topobank.analysis.models import Analysis

class Command(BaseCommand):
    help = "Deletes a user and all associated data (topographies, files). Handle with care."

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)

    def handle(self, *args, **options):

        user = User.objects.get(username=options['username'])

        surfaces = Surface.objects.filter(user=user)
        topographies = Topography.objects.filter(surface__in=surfaces)
        analyses = Analysis.objects.filter(topography__in=topographies)

        analyses.delete()
        topographies.delete()
        surfaces.delete()
        user.delete()

        self.stdout.write(self.style.SUCCESS(
            "Removed user '{}' and everything related.".format(options['username'])))
