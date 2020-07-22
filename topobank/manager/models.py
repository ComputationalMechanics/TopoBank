from django.db import models
from django.shortcuts import reverse
from django.core.cache import cache
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.files import File

from guardian.shortcuts import assign_perm, remove_perm, get_users_with_perms
import tagulous.models as tm

from .utils import get_topography_reader

from topobank.users.models import User
from topobank.publication.models import Publication
from topobank.users.utils import get_default_group

import logging
_log = logging.getLogger(__name__)

MAX_LENGTH_DATAFILE_FORMAT = 15  # some more characters than currently needed, we may have sub formats in future


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'topographies/user_{0}/{1}'.format(instance.surface.creator.id, filename)


class AlreadyPublishedException(Exception):
    pass


class TagModel(tm.TagTreeModel):
    """This is the common tag model for surfaces and topographies.
    """
    class TagMeta:
        force_lowercase = True
        # not needed yet
        # autocomplete_view = 'manager:autocomplete-tags'


class PublishedSurfaceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(publication__isnull=True)


class Surface(models.Model):
    """Physical Surface.

    There can be many topographies (measurements) for one surface.
    """
    CATEGORY_CHOICES = [
        ('exp', 'Experimental data'),
        ('sim', 'Simulated data'),
        ('dum', 'Dummy data')
    ]

    LICENSE_CHOICES = [
        ('cc0-1.0', 'CC0 (Public Domain Dedication)'),
        # https://creativecommons.org/publicdomain/zero/1.0/
        ('ccby-4.0', 'CC BY 4.0'),
        # https://creativecommons.org/licenses/by/4.0/
        ('ccbysa-4.0', 'CC BY-SA 4.0'),
        # https://creativecommons.org/licenses/by-sa/4.0/
    ]

    name = models.CharField(max_length=80)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    category = models.TextField(choices=CATEGORY_CHOICES, null=True, blank=False)  # TODO change in character field
    tags = tm.TagField(to=TagModel)

    objects = models.Manager()
    published = PublishedSurfaceManager()

    class Meta:
        ordering = ['name']
        permissions = (
            ('share_surface', 'Can share surface'),
            ('publish_surface', 'Can publish surface'),
        )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('manager:surface-detail', kwargs=dict(pk=self.pk))

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

        #
        # Request all standard analyses to be available for that user
        #
        _log.info("After sharing surface %d with user %d, requesting all standard analyses..", self.id, with_user.id)
        from topobank.analysis.models import AnalysisFunction
        from topobank.analysis.utils import request_analysis
        auto_analysis_funcs = AnalysisFunction.objects.filter(automatic=True)
        for topo in self.topography_set.all():
            for af in auto_analysis_funcs:
                request_analysis(with_user, af, topo)  # standard arguments

    def unshare(self, with_user):
        """Remove share on this surface for given user.

        If the user has no permissions, nothing happens.

        :param with_user: User to remove share from
        """
        for perm in ['view_surface', 'change_surface']:
            if with_user.has_perm(perm, self):
                remove_perm(perm, with_user, self)

    def deepcopy(self):
        """Creates a copy of this surface with all topographies and meta data.

        The database entries for this surface and all related
        topographies are copied, therefore all meta data.
        All files will be copied.

        The automated analyses will be triggered for this new surface.

        Returns
        -------
        The copy of the surface.

        """
        # Copy of the surface entry
        # (see https://docs.djangoproject.com/en/2.2/topics/db/queries/#copying-model-instances)

        copy = Surface.objects.get(pk=self.pk)
        copy.pk = None
        copy.tags = self.tags.get_tag_list()
        copy.save()

        for topo in self.topography_set.all():
            new_topo = topo.deepcopy(copy)
            # we pass the surface here because there is a contraint that (surface_id + topography name)
            # must be unique, i.e. a surface should never have two topographies of the same name,
            # so we can't set the new surface as the second step
            new_topo.renew_analyses()

        _log.info("Created deepcopy of surface %s -> surface %s", self.pk, copy.pk)
        return copy

    def publish(self, license):
        """Publish surface.

        An immutable copy is created along with a publication entry.
        The latter is returned.

        Parameters
        ----------
        license: str
            One of the keys of LICENSE_CHOICES

        Returns
        -------
        Publication
        """
        if self.is_published:
            raise AlreadyPublishedException()

        #
        # Create a copy of this surface
        #
        copy = self.deepcopy()

        #
        # Remove edit, share and delete permission from everyone
        #
        users = get_users_with_perms(self)
        for u in users:
            for perm in ['publish_surface', 'share_surface', 'change_surface', 'delete_surface']:
                remove_perm(perm, u, copy)

        #
        # Add read permission for everyone
        #
        assign_perm('view_surface', get_default_group(), copy)

        #
        # Create publication
        #
        latest_publication = Publication.objects.filter(original_surface=self).order_by('version').last()
        if latest_publication:
            version = latest_publication.version + 1
        else:
            version = 1

        pub = Publication.objects.create(surface=copy, original_surface=self,
                                         license=license, version=version, publisher=self.creator)

        _log.info(f"Published surface {self.name} (id: {self.id}) "+\
                  f"with license {license}, version {version}")
        _log.info(f"URL of publication: {pub.get_absolute_url()}")

        return pub

    @property
    def is_published(self):
        return hasattr(self, 'publication')  # checks whether the related object surface.publication exists


class Topography(models.Model):
    """Topography Measurement of a Surface.
    """

    # TODO After upgrade to Django 2.2, use contraints: https://docs.djangoproject.com/en/2.2/ref/models/constraints/
    class Meta:
        ordering = ['name']
        unique_together = (('surface', 'name'),)

    LENGTH_UNIT_CHOICES = [
        ('km', 'kilometers'),
        ('m','meters'),
        ('mm', 'millimeters'),
        ('µm', 'micrometers'),
        ('nm', 'nanometers'),
        ('Å', 'angstrom'),
    ]

    DETREND_MODE_CHOICES = [
        ('center', 'No detrending, but substract mean height'),
        ('height', 'Remove tilt'),
        ('curvature', 'Remove curvature'),
    ]

    verbose_name_plural = 'topographies'

    #
    # Descriptive fields
    #
    surface = models.ForeignKey('Surface', on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    creator = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    measurement_date = models.DateField()
    description = models.TextField(blank=True)
    tags = tm.TagField(to=TagModel)

    #
    # Fields related to raw data
    #
    datafile = models.FileField(max_length=250, upload_to=user_directory_path)  # currently upload_to not used in forms
    datafile_format = models.CharField(max_length=MAX_LENGTH_DATAFILE_FORMAT,
                                       null=True, default=None, blank=True)
    data_source = models.IntegerField()
    # Django documentation discourages the use of null=True on a CharField. I'll use it here
    # nevertheless, because I need this values as argument to a function where None has
    # a special meaning (autodetection of format). If I would use an empty string
    # as proposed in the docs, I would have to implement extra logic everywhere the field
    # 'datafile_format' is used.

    #
    # Fields with physical meta data
    #
    size_editable = models.BooleanField(default=False)
    size_x = models.FloatField()
    size_y = models.FloatField(null=True)  # null for line scans

    unit_editable = models.BooleanField(default=False)
    unit = models.TextField(choices=LENGTH_UNIT_CHOICES)

    height_scale_editable = models.BooleanField(default=False)
    height_scale = models.FloatField(default=1)

    detrend_mode = models.TextField(choices=DETREND_MODE_CHOICES, default='center')

    resolution_x = models.IntegerField(null=True)  # null for line scans TODO really?
    resolution_y = models.IntegerField(null=True)  # null for line scans

    is_periodic = models.BooleanField(default=False)

    #
    # Methods
    #
    def __str__(self):
        return "Topography '{0}' from {1}".format(\
            self.name, self.measurement_date)

    def get_absolute_url(self):
        return reverse('manager:topography-detail', kwargs=dict(pk=self.pk))

    def cache_key(self):
        return f"topography-{self.id}-channel-{self.data_source}"

    def topography(self):
        """Return a SurfaceTopography.Topography/UniformLineScan/NonuniformLineScan instance.

        This instance is guaranteed to

        - have an info dict with 'unit' key: .info['unit']
        - have a size: .physical_sizes
        - scaled and detrended with the saved parameters

        """
        cache_key = self.cache_key()

        #
        # Try to get topography from cache if possible
        #
        topo = cache.get(cache_key)
        if topo is None:
            toporeader = get_topography_reader(self.datafile, format=self.datafile_format)
            topography_kwargs = dict(channel_index=self.data_source,
                                     periodic=self.is_periodic)

            # Set size if physical size was not given in datafile
            # (see also  TopographyCreateWizard.get_form_initial)
            # Physical size is always a tuple.
            if self.size_editable: # TODO: could be removed in favor of "channel_dict['physical_sizes'] is None"
                if self.size_y is None:
                    topography_kwargs['physical_sizes'] = self.size_x,
                else:
                    topography_kwargs['physical_sizes'] = self.size_x, self.size_y

            if self.height_scale_editable:
                # Adjust height scale to value chosen by user
                topography_kwargs['height_scale_factor'] = self.height_scale

                # from SurfaceTopography.read_topography's docstring:
                #
                # height_scale_factor : float
                #    Override height scale factor found in the data file.
                #
                # So default is to use the factor from the file.

            # Eventually get topography from module "SurfaceTopography" using the given keywords
            topo = toporeader.topography(**topography_kwargs)
            topo = topo.detrend(detrend_mode=self.detrend_mode, info=dict(unit=self.unit))

            cache.set(cache_key, topo)
            # be sure to invalidate the cache key if topography is saved again -> signals.py

        return topo

    def renew_analyses(self):
        """Submit all automatic analysis for this topography.

        Before make sure to delete all analyses for same topography,
        they all can be wrong if this topography changed.

        TODO Maybe also renew all already existing analyses with different parameters?

        Implementation Note:

        This method cannot be easily used in a post_save signal,
        because the pre_delete signal deletes the datafile and
        this also then triggers "renew_analyses".
        """
        from topobank.analysis.utils import submit_analysis
        from topobank.analysis.models import AnalysisFunction, Analysis
        from guardian.shortcuts import get_users_with_perms

        auto_analysis_funcs = AnalysisFunction.objects.filter(automatic=True)

        # collect users which are allowed to view analyses
        users = get_users_with_perms(self.surface)

        def submit_all(instance=self):
            for af in auto_analysis_funcs:
                Analysis.objects.filter(function=af, topography=instance).delete()
                try:
                    submit_analysis(users, af, instance)
                except Exception as err:
                    _log.error("Cannot submit analysis for function '%s' and topography %d. Reason: %s",
                               af.name, instance.id, str(err))

        transaction.on_commit(lambda: submit_all(self))

    def to_dict(self):
        """Create dictionary for export of metadata to json or yaml"""
        return {'name': self.name,
                'data_source': self.data_source,
                'creator': {'name': self.creator.name, 'orcid': self.creator.orcid_id},
                'measurement_date': self.measurement_date,
                'description': self.description,
                'unit': self.unit,
                'height_scale': self.height_scale,
                'size': (self.size_x, self.size_y)}

    def deepcopy(self, to_surface):
        """Creates a copy of this topography with all data files copied.

        Parameters
        ----------
        to_surface: Surface
            target surface

        Returns
        -------
        The copied topography.

        """

        copy = Topography.objects.get(pk=self.pk)
        copy.pk = None
        copy.surface = to_surface

        with self.datafile.open(mode='rb') as datafile:
            copy.datafile = default_storage.save(self.datafile.name, File(datafile))

        copy.tags = self.tags.get_tag_list()
        copy.save()

        return copy

