from django.db import models, transaction
from guardian.shortcuts import assign_perm, remove_perm

from .utils import TopographyFile, selected_topographies, TopographyFileException
from topobank.users.models import User


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'topographies/user_{0}/{1}'.format(instance.surface.user.id, filename)

class Surface(models.Model):
    """Physical Surface.

    There can be many topographies (measurements) for one surface.
    """
    CATEGORY_CHOICES = [
        ('exp', 'Experimental data'),
        ('sim', 'Simulated data'),
        ('dum', 'Dummy data')
    ]

    name = models.CharField(max_length=80)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    category = models.TextField(choices=CATEGORY_CHOICES, null=True, blank=False) #  TODO change in character field

    class Meta:
        permissions = (
            ('share_surface', 'Can share surface'),
        )

    def num_topographies(self):
        return self.topography_set.count()

    def is_shared(self, with_user, allow_change=False):
        """Returns True, if this surface is shared with a given user.

        Always returns True if user is the creator.

        :param with_user: User to test
        :param allow_change: If True, only return True if surface can be changed by given user
        :return: True or False
        """
        result = with_user.has_perm('view_surface', self)
        if result and allow_change:
            result = with_user.has_perm('change_surface', self)
        return result


    def share(self, with_user, allow_change=False):
        """Share this surface with a given user.

        :param with_user: user to share with
        :param allow_change: if True, also allow changing the surface
        """
        assign_perm('view_surface', with_user, self)
        if allow_change:
            assign_perm('change_surface', with_user, self)

    def unshare(self, with_user):
        """Remove share on this surface for given user.

        If the user has no permissions, nothing happens.

        :param with_user: User to remove share from
        """
        for perm in ['view_surface', 'change_surface']:
            if with_user.has_perm(perm, self):
                remove_perm(perm, with_user, self)

class Topography(models.Model):
    """Topography Measurement of a Surface.
    """

    LENGTH_UNIT_CHOICES = [
        # (None, '(unknown)') # TODO should this be allowed?
        ('km', 'kilometers'),
        ('m','meters'),
        ('mm', 'millimeters'),
        ('µm', 'micrometers'),
        ('nm', 'nanometers'),
        ('Å', 'angstrom'),
    ]

    DETREND_MODE_CHOICES = [
        ('center', 'No detrending'),
        ('height', 'Remove tilt'),
        ('curvature', 'Remove curvature'),
    ]

    verbose_name_plural = 'topographies'

    #
    # Description fields
    #
    surface = models.ForeignKey('Surface', on_delete=models.CASCADE)
    name = models.CharField(max_length=80)

    datafile = models.FileField(max_length=250, upload_to=user_directory_path) # currently upload_to not used in forms
    data_source = models.IntegerField()
    measurement_date = models.DateField()
    description = models.TextField(blank=True)

    #
    # Fields with physical meta data
    #
    size_editable = models.BooleanField(default=False)
    size_x = models.FloatField()
    size_y = models.FloatField(null=True) # null for line scans

    unit_editable = models.BooleanField(default=False)
    unit = models.TextField(choices=LENGTH_UNIT_CHOICES)

    height_scale_editable = models.BooleanField(default=False)
    height_scale = models.FloatField(default=1)

    detrend_mode = models.TextField(choices=DETREND_MODE_CHOICES, default='center')

    resolution_x = models.IntegerField(null=True) # null for line scans
    resolution_y = models.IntegerField(null=True) # null for line scans

    #
    # Methods
    #
    def __str__(self):
        return "Topography '{0}' from {1}".format(\
            self.name, self.measurement_date)

    def topography(self):
        """Return a PyCo Topography/Line Scan instance.

        This instance is guaranteed to

        - have an info dict with 'unit' key: .info['unit']
        - have a size: .size
        - scaled and detrended with the saved parameters

        """
        try:
            file = self.datafile.file
        except Exception as exc:
            msg = "Problems while instatiating file '{}' from storage '{}'.".format(
                self.datafile.name, self.datafile.storage)
            msg += " Further info: {}".format(exc)
            raise TopographyFileException(msg) from exc

        if not hasattr(file, 'mode'):
            # WORKAROUND in order to make PyCo's "detect_format" (Version 0.31)
            # work with S3 backend. The S3 backend file has no attribute "mode"
            # and so "detect_format" does not work, because this attribute
            # is used to find out whether the stream is binary or not.
            # TODO Is this workaround still needed with the new reader infrastructure in PyCo
            file.mode = 'rb'

        topofile = TopographyFile(file)

        topo = topofile.topography(int(self.data_source))
        # TODO int() is a fix for SQLite which cannot return real int?? remove for PG

        #
        # Now prepare topography using the parameters from database
        #

        # set size if physical size was not given in datafile
        # (see also  TopographyCreateWizard.get_form_initial)

        if self.size_editable:
            if self.size_y is None:
                topo.size = self.size_x, # size is now always a tuple
            else:
                topo.size = self.size_x, self.size_y

        topo = topo.scale(self.height_scale).detrend(detrend_mode=self.detrend_mode,
                                                     info=dict(unit=self.unit))

        return topo

    def submit_automated_analyses(self):
        """Submit all automatic analysis for this Topography.
        """
        from topobank.taskapp.tasks import submit_analysis
        from topobank.analysis.models import AnalysisFunction

        auto_analysis_funcs = AnalysisFunction.objects.filter(automatic=True)

        def submit_all(instance=self):
            for af in auto_analysis_funcs:
                submit_analysis(af, instance)

        transaction.on_commit(lambda: submit_all(self))



