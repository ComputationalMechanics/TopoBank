import pytest

from topobank.manager.tests.utils import TopographyFactory


@pytest.mark.django_db
def test_thumbnail_exists_for_new_topography():
    topo = TopographyFactory(size_x=1, size_y=1)
    # should have a thumbnail picture
    assert topo.thumbnail is not None

