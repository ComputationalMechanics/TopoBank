"""
Tests for the interface to topography files
and other things in topobank.manager.utils
"""

import pytest
from pathlib import Path

from ..tests.utils import two_topos
from ..utils import TopographyFile, DEFAULT_DATASOURCE_NAME, \
    selection_to_topographies, selection_for_select_all, selection_choices


def test_data_sources_txt():

    input_file_path = Path('topobank/manager/fixtures/example4.txt')  # TODO use standardized way to find files

    topofile = TopographyFile(input_file_path)

    assert topofile.data_sources == [DEFAULT_DATASOURCE_NAME]


@pytest.fixture
def mock_topos(mocker):
    mocker.patch('topobank.manager.models.Topography', autospec=True)
    mocker.patch('topobank.manager.models.Surface', autospec=True)

@pytest.fixture
def testuser(django_user_model):
    username = 'testuser'
    user, created = django_user_model.objects.get_or_create(username=username)
    return user

def test_selection_to_topographies(testuser, mock_topos):

    from topobank.manager.models import Topography

    selection = ('topography-1', 'topography-2', 'surface-1')
    selection_to_topographies(selection, testuser)

    Topography.objects.filter.assert_called_with(surface__user=testuser, id__in=[1,2])

def test_selection_to_topographies_with_given_surface(testuser, mock_topos):

    from topobank.manager.models import Topography, Surface

    surface = Surface(name='surface1')

    selection = ('topography-1', 'topography-2', 'surface-1')
    selection_to_topographies(selection, testuser, surface=surface)

    Topography.objects.filter.assert_called_with(surface__user=testuser, id__in=[1,2], surface=surface)

def test_select_all(two_topos, testuser):
    selection = selection_for_select_all(testuser)
    assert ['surface-1'] == selection

def test_selection_choices(two_topos, testuser):
    selection = selection_choices(testuser)
    assert [('surface-1', 'surface1'),
            ('topography-1', 'Example 3 - ZSensor'),
            ('topography-2', 'Example 4 - Default')] == selection

