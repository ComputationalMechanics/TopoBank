import pytest

from django.shortcuts import reverse

from topobank.manager.tests.utils import TopographyFactory, UserFactory
from .utils import AnalysisFunctionFactory
from ..views import card_view_class, SimpleCardView, PlotCardView, switch_card_view

@pytest.mark.django_db
def test_card_templates(client, mocker):

    #
    # Create database objects
    #
    password = "secret"
    user = UserFactory(password=password)
    func1 = AnalysisFunctionFactory()
    topo1 = TopographyFactory()


    assert client.login(username=user.username, password=password)

    def dummy(t):
        return {'name': 'Some result for {}'.format(t) }
    dummy.card_view_flavor = 'simple'

    #
    # Mock to return this dummy function
    #
    m = mocker.patch('topobank.analysis.models.AnalysisFunction.python_function', new_callable=mocker.PropertyMock)
    m.return_value = dummy

    # test the mocking
    assert func1.python_function(1) == { 'name': 'Some result for 1'}
    assert func1.card_view_flavor == 'simple'

    response = client.get(reverse('analysis:card'), data={
        'function_id': func1.id,
        'card_id': 'card',
        'template_flavor': 'list',
        'topography_ids[]': [topo1.id],
    }, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # we need an AJAX request

    assert response.template_name == [ 'analysis/simple_card_list.html']

    response = client.get(reverse('analysis:card'), data={
        'function_id': func1.id,
        'card_id': 'card',
        'template_flavor': 'detail',
        'topography_ids[]': [topo1.id],
    }, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # we need an AJAX request

    assert response.template_name == [ 'analysis/simple_card_detail.html']

def test_card_view_class():
    assert card_view_class('simple') == SimpleCardView
    assert card_view_class('plot') == PlotCardView