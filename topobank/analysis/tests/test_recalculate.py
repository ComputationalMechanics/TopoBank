from django.shortcuts import reverse
from notifications.models import Notification
import pytest
from django.db import transaction

from topobank.manager.tests.utils import SurfaceFactory, TopographyFactory, UserFactory
from topobank.analysis.tests.utils import AnalysisFunctionFactory
from topobank.analysis.models import Analysis, AnalysisCollection

@pytest.mark.django_db
def test_recalculate(client):

    user = UserFactory()
    surface = SurfaceFactory(creator=user)
    topo1 = TopographyFactory(surface=surface)
    topo2 = TopographyFactory(surface=surface)
    func = AnalysisFunctionFactory(name="test function")

    client.force_login(user)

    with transaction.atomic():
        # trigger "recalculate" for two topographies
        response = client.post(reverse('analysis:card-submit'), {
            'function_id': func.id,
            'topography_ids[]': [topo1.id, topo2.id],
            'function_kwargs_json': '{}'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # we need an AJAX request
        assert response.status_code == 200

    #
    # Analysis objects should be there and marked for the user
    #
    analysis1 = Analysis.objects.get(function=func, topography=topo1)
    analysis2 = Analysis.objects.get(function=func, topography=topo2)

    assert user in analysis1.users.all()
    assert user in analysis2.users.all()

    #
    # Don't know yet how execute tasks locally without task queue
    # Celery's "task_always_eager" is not suitable for unit testing.
    #
    #
    # assert analysis1.task_state == 'su'
    # assert analysis2.task_state == 'su'
    #
    # #
    # # Collection object should be there and contain those analyses
    # #
    # collection = AnalysisCollection.objects.get(owner=user)
    #
    # assert collection.analyses.count() == 2
    # assert analysis1 in collection.analyses.all()
    # assert analysis2 in collection.analyses.all()
    #
    # #
    # # Notification should be there, since the task has already performed
    # #
    # note = Notification.objects.get(recipient=user, description__contains="Tasks finished")
    # assert note.href == reverse('analysis:collection', kwargs=dict(collection_id=collection.id))

