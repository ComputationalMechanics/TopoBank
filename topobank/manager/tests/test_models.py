import pytest

from django.db.utils import IntegrityError
from django.db import transaction
from notifications.signals import notify
from notifications.models import Notification

from ..models import Topography, Surface
from .utils import two_topos, SurfaceFactory, UserFactory, TopographyFactory

@pytest.mark.django_db
def test_topography_name(two_topos):
    topos = Topography.objects.all().order_by('name')
    assert [ t.name for t in topos ] == ['Example 3 - ZSensor',
                                         'Example 4 - Default']

@pytest.mark.django_db
def test_topography_has_periodic_flag(two_topos):
    topos = Topography.objects.all().order_by('name')
    assert not topos[0].is_periodic
    assert not topos[1].is_periodic


@pytest.mark.django_db
def test_topography_str(two_topos):
    surface = Surface.objects.get(name="Surface 1")
    topos = Topography.objects.filter(surface=surface).order_by('name')
    assert [ str(t) for t in topos ] == ["Topography 'Example 3 - ZSensor' from 2018-01-01"]

    surface = Surface.objects.get(name="Surface 2")
    topos = Topography.objects.filter(surface=surface).order_by('name')
    assert [str(t) for t in topos] == ["Topography 'Example 4 - Default' from 2018-01-02"]


@pytest.mark.django_db
def test_call_topography_method_multiple_times(two_topos):
    topo = Topography.objects.get(name="Example 3 - ZSensor")

    #
    # coeffs should not change in between calls
    #
    st_topo = topo.topography()

    coeffs_before = st_topo.coeffs
    scaling_factor_before = st_topo.parent_topography.scale_factor
    st_topo = topo.topography()

    assert st_topo.parent_topography.scale_factor == scaling_factor_before
    assert st_topo.coeffs == coeffs_before


@pytest.mark.django_db
def test_unique_topography_name_in_same_surface():

    user = UserFactory()
    surface1 = SurfaceFactory(creator=user)

    TopographyFactory(surface=surface1, name='TOPO')

    with transaction.atomic(): # otherwise we can't proceed in this test
        with pytest.raises(IntegrityError):
            TopographyFactory(surface=surface1, name='TOPO')

    # no problem with another surface
    surface2 = SurfaceFactory(creator=user)
    TopographyFactory(surface=surface2, name='TOPO')

@pytest.mark.django_db
def test_surface_description(django_user_model):

    username = "testuser"
    password = "abcd$1234"

    user = django_user_model.objects.create_user(username=username, password=password)

    surface = Surface.objects.create(name='Surface 1', creator=user)

    assert ""==surface.description

    surface.description = "First surface"

    surface.save()

    surface = Surface.objects.get(name='Surface 1')
    assert "First surface" == surface.description

@pytest.mark.django_db
def test_surface_share_and_unshare():

    password = "abcd$1234"

    user1 = UserFactory(password=password)
    user2 = UserFactory(password=password)

    surface = SurfaceFactory(creator=user1)

    #
    # no permissions at beginning
    #
    assert not user2.has_perm('view_surface', surface)

    #
    # first: share, but only with view access
    #
    surface.share(user2) # default: only view access
    assert user2.has_perm('view_surface', surface)
    assert not user2.has_perm('change_surface', surface)
    assert not user2.has_perm('delete_surface', surface)
    assert not user2.has_perm('share_surface', surface)

    #
    # second: share, but also with right access
    #
    surface.share(user2, allow_change=True)  # default: only view access
    assert user2.has_perm('view_surface', surface)
    assert user2.has_perm('change_surface', surface)
    assert not user2.has_perm('delete_surface', surface)
    assert not user2.has_perm('share_surface', surface)

    #
    # third: remove all shares again
    #
    surface.unshare(user2)
    assert not user2.has_perm('view_surface', surface)
    assert not user2.has_perm('change_surface', surface)
    assert not user2.has_perm('delete_surface', surface)
    assert not user2.has_perm('share_surface', surface)

    # no problem to call this removal again
    surface.unshare(user2)

@pytest.mark.django_db
def test_other_methods_about_sharing():

    user1 = UserFactory()
    user2 = UserFactory()

    # create surface, at first user 2 has no access
    surface = SurfaceFactory(creator=user1)
    assert not surface.is_shared(user2)
    assert not surface.is_shared(user2, allow_change=True)

    # now share and test access
    surface.share(user2)

    assert surface.is_shared(user2)
    assert not surface.is_shared(user2, allow_change=True)

    # .. add permission to change
    surface.share(user2, allow_change=True)
    assert surface.is_shared(user2)
    assert surface.is_shared(user2, allow_change=True)

    # .. remove all permissions
    surface.unshare(user2)
    assert not surface.is_shared(user2)
    assert not surface.is_shared(user2, allow_change=True)

@pytest.mark.django_db
def test_notifications_are_deleted_when_surface_deleted():

    password = "abcd$1234"
    user = UserFactory(password=password)
    surface = SurfaceFactory(creator=user)
    surface_id = surface.id

    notify.send(sender=user, verb="create", target=surface, recipient=user, description="You have a new surface")
    notify.send(sender=user, verb="info", target=surface, recipient=user, description="Another info.")

    from django.contrib.contenttypes.models import ContentType
    ct = ContentType.objects.get_for_model(surface)

    assert Notification.objects.filter(target_content_type=ct, target_object_id=surface_id).count() == 2

    #
    # now delete the surface, the notification is no longer valid and should be also deleted
    #
    surface.delete()

    assert Notification.objects.filter(target_content_type=ct, target_object_id=surface_id).count() == 0

@pytest.mark.django_db
def test_notifications_are_deleted_when_topography_deleted():

    password = "abcd$1234"
    user = UserFactory(password=password)
    surface = SurfaceFactory(creator=user)

    topo = TopographyFactory(surface=surface)
    topo_id = topo.id

    notify.send(sender=user, verb="create", target=topo, recipient=user, description="You have a new topography")
    notify.send(sender=user, verb="info", target=topo, recipient=user, description="Another info.")

    from django.contrib.contenttypes.models import ContentType
    ct = ContentType.objects.get_for_model(topo)

    assert Notification.objects.filter(target_content_type=ct, target_object_id=topo_id).count() == 2

    #
    # now delete the topography, the notification is no longer valid and should be also deleted
    #
    topo.delete()

    assert Notification.objects.filter(target_content_type=ct, target_object_id=topo_id).count() == 0









