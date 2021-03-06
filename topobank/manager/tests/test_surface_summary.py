import pytest
from pytest import approx

from dataclasses import dataclass

from django.shortcuts import reverse

from ..models import Topography
from ..utils import bandwidths_data

from .utils import TopographyFactory, topography_loaded_from_broken_file
from topobank.utils import assert_in_content

@pytest.fixture
def two_topos_mock(mocker):

    @dataclass  # new feature in Python 3.7
    class STTopoStub:  # ST: from module SurfaceTopography
        bandwidth: tuple
        info: dict

    topography_method_mock = mocker.patch('topobank.manager.models.Topography.topography')
    topography_method_mock.side_effect = [
        STTopoStub(bandwidth=lambda: (6, 600), info=dict(unit='nm')),
        STTopoStub(bandwidth=lambda: (5, 100), info=dict(unit='µm')),
    ]
    mocker.patch('topobank.manager.models.Topography', autospec=True)

    reverse_patch = mocker.patch('topobank.manager.utils.reverse')
    reverse_patch.side_effect = [
        'linkB/', 'linkA/'
    ]

    # for bandwidths_data():
    #   needed from SurfaceTopography.Topography: pixel_size, size
    #   needed from TopoBank's Topography: name, pk

    topos = [Topography(name='topoB', pk=2), Topography(name='topoA', pk=1)]

    return topos


def test_bandwidths_data(two_topos_mock):

    bd = bandwidths_data(two_topos_mock)

    topoB, topoA = two_topos_mock

    # expected bandwidth data - smaller lower bounds should be listed first
    exp_bd = [
        dict(upper_bound=6e-7, lower_bound=6e-9, topography=topoB, link='linkB/'),
        dict(upper_bound=1e-4, lower_bound=5e-6, topography=topoA, link='linkA/'),
    ]

    for i in range(len(exp_bd)):
        for field in ['upper_bound', 'lower_bound']:
            assert exp_bd[i][field] == approx(bd[i][field])
        for field in ['topography', 'link']:
            assert exp_bd[i][field] == bd[i][field]


@pytest.mark.django_db
def test_bandwidth_with_angstrom():

    topo = TopographyFactory(unit='Å')
    bd = bandwidths_data([topo])

    assert len(bd) == 1


@pytest.mark.django_db
def test_bandwidth_error_message_in_dict_when_problems_while_loading(topography_loaded_from_broken_file):

    #
    # Theoretically loading of a topography can fail during
    # creation of the bandwidth plot, although it worked before.
    # This can happen e.g. because of an update of the SurfaceTopography package
    # which may introduce new errors.
    # In this case the bandwidths_data function should return entries with errors.
    #

    topo1 = topography_loaded_from_broken_file
    topo2 = TopographyFactory()
    bd = bandwidths_data([topo1, topo2])
    assert len(bd) == 2

    bd1, bd2 = bd

    # first one should indicate that there is an error
    assert bd1['topography'] == topo1
    assert bd1['error_message'] == f"Topography '{topo1.name}' (id: {topo1.id}) cannot be loaded unexpectedly."
    assert 'Failure loading' in bd1['link']
    assert "id: {}".format(topo1.id) in bd1['link']
    assert bd1['lower_bound'] is None
    assert bd1['upper_bound'] is None

    # first one should be okay (no errors)
    assert bd2['topography'] == topo2
    assert bd2['error_message'] is None  # No error
    assert bd2['lower_bound'] is not None
    assert bd2['upper_bound'] is not None


@pytest.mark.django_db
def test_bandwidth_error_message_in_UI_when_problems_while_loading(client, topography_loaded_from_broken_file,
                                                                   handle_usage_statistics):
    #
    # Theoretically loading of a topography can fail during
    # creation of the bandwidth plot, although it worked before.
    # This can happen e.g. because of an update of the SurfaceTopography package
    # which may introduce new errors.
    # In this case the user should see an error message in the UI.
    #
    surface = topography_loaded_from_broken_file.surface
    user = surface.creator

    client.force_login(user=user)

    response = client.get(reverse('manager:surface-detail', kwargs=dict(pk=surface.pk)))
    assert response.status_code == 200

    assert_in_content(response, f"{topography_loaded_from_broken_file.name}")
    assert_in_content(response, f"(id: {topography_loaded_from_broken_file.id}) cannot be loaded unexpectedly.")
    assert_in_content(response, "send us an e-mail about this issue")
