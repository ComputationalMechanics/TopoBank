from django.contrib.staticfiles.templatetags.staticfiles import static
from django.conf import settings
from django.shortcuts import reverse
import django

import json
import bokeh
import celery

import SurfaceTopography, ContactMechanics, NuMPI, muFFT

from topobank.manager.utils import current_selection_as_basket_items

UNSELECT_ALL_URL = reverse('manager:unselect-all')


def versions_processor(request):

    # key 'links': dicts with keys display_name:url
    versions = [
        dict(module='TopoBank',
             version=settings.TOPOBANK_VERSION,
             links={'Website':'https://github.com/ComputationalMechanics/TopoBank',
                    'Changelog': static('other/CHANGELOG.md')}), # needs 'manage.py collectstatic' before!
        dict(module='SurfaceTopography',
             version=SurfaceTopography.__version__,
             links={'Website': 'https://github.com/ComputationalMechanics/SurfaceTopography',
                    'Changelog': f'https://github.com/ComputationalMechanics/SurfaceTopography/blob/{SurfaceTopography.__version__}/SurfaceTopography/ChangeLog.md'}),
        dict(module='ContactMechanics',
             version=ContactMechanics.__version__,
             links={'Website': 'https://github.com/ComputationalMechanics/ContactMechanics',#
                    'Changelog': f'https://github.com/ComputationalMechanics/ContactMechanics/blob/{ContactMechanics.__version__}/ContactMechanics/ChangeLog.md'}),
        dict(module='NuMPI',
             version=NuMPI.__version__,
             links={'Website': 'https://github.com/IMTEK-Simulation/NuMPI',
                    'Changelog': f'https://github.com/IMTEK-Simulation/NuMPI/blob/{NuMPI.__version__}/ChangeLog.md'}),
        dict(module='muFFT',
             version=muFFT.version.description(),
             links={'Website': 'https://gitlab.com/muspectre/muspectre',
                    'Changelog': f'https://gitlab.com/muspectre/muspectre/-/blob/{muFFT.version.description()}/CHANGELOG.md'}),
        dict(module='Django',
             version=django.__version__,
             links={'Website': 'https://www.djangoproject.com/'}),
        dict(module='Celery',
             version=celery.__version__,
             links={'Website': 'http://www.celeryproject.org/'}),
        dict(module='Bokeh',
             version=bokeh.__version__,
             links={'Website': 'https://bokeh.pydata.org/en/latest/'}),
    ]

    return dict(versions=versions, contact_email_address=settings.CONTACT_EMAIL_ADDRESS)


def basket_processor(request):
    """Return JSON with select surfaces and topographies.

    Parameters
    ----------
    request

    Returns
    -------
    Dict with extra context, a key 'basket_items_json'
    which encodes all selected topographies and surfaces such they can be
    displayed on top of each page. See also base.html.
    """
    basket_items = current_selection_as_basket_items(request)

    return dict(basket_items_json=json.dumps(basket_items),
                num_basket_items=len(basket_items),
                unselect_all_url=UNSELECT_ALL_URL)

