"""
Functions which can be chosen for analysis of topographies.

The first argument is always a SurfaceTopography.Topography!
"""

import numpy as np
import tempfile

# These imports are needed for storage
from django.core.files.storage import default_storage
from django.core.files import File
import xarray as xr

from SurfaceTopography import Topography, PlasticTopography

from ContactMechanics import PeriodicFFTElasticHalfSpace, FreeFFTElasticHalfSpace, make_system

CONTACT_MECHANICS_KWARGS_LIMITS = {
            'nsteps': dict(min=1, max=50),
            'maxiter': dict(min=1, max=1000),
            'pressures': dict(maxlen=50),
}

# TODO: _unicode_map and super and subscript functions should be moved to some support module.

_unicode_map = {
    # superscript subscript
    '0': ('\u2070', '\u2080'),
    '1': ('\u00B9', '\u2081'),
    '2': ('\u00B2', '\u2082'),
    '3': ('\u00B3', '\u2083'),
    '4': ('\u2074', '\u2084'),
    '5': ('\u2075', '\u2085'),
    '6': ('\u2076', '\u2086'),
    '7': ('\u2077', '\u2087'),
    '8': ('\u2078', '\u2088'),
    '9': ('\u2079', '\u2089'),
    'a': ('\u1d43', '\u2090'),
    'b': ('\u1d47', '?'),
    'c': ('\u1d9c', '?'),
    'd': ('\u1d48', '?'),
    'e': ('\u1d49', '\u2091'),
    'f': ('\u1da0', '?'),
    'g': ('\u1d4d', '?'),
    'h': ('\u02b0', '\u2095'),
    'i': ('\u2071', '\u1d62'),
    'j': ('\u02b2', '\u2c7c'),
    'k': ('\u1d4f', '\u2096'),
    'l': ('\u02e1', '\u2097'),
    'm': ('\u1d50', '\u2098'),
    'n': ('\u207f', '\u2099'),
    'o': ('\u1d52', '\u2092'),
    'p': ('\u1d56', '\u209a'),
    'q': ('?', '?'),
    'r': ('\u02b3', '\u1d63'),
    's': ('\u02e2', '\u209b'),
    't': ('\u1d57', '\u209c'),
    'u': ('\u1d58', '\u1d64'),
    'v': ('\u1d5b', '\u1d65'),
    'w': ('\u02b7', '?'),
    'x': ('\u02e3', '\u2093'),
    'y': ('\u02b8', '?'),
    'z': ('?', '?'),
    'A': ('\u1d2c', '?'),
    'B': ('\u1d2e', '?'),
    'C': ('?', '?'),
    'D': ('\u1d30', '?'),
    'E': ('\u1d31', '?'),
    'F': ('?', '?'),
    'G': ('\u1d33', '?'),
    'H': ('\u1d34', '?'),
    'I': ('\u1d35', '?'),
    'J': ('\u1d36', '?'),
    'K': ('\u1d37', '?'),
    'L': ('\u1d38', '?'),
    'M': ('\u1d39', '?'),
    'N': ('\u1d3a', '?'),
    'O': ('\u1d3c', '?'),
    'P': ('\u1d3e', '?'),
    'Q': ('?', '?'),
    'R': ('\u1d3f', '?'),
    'S': ('?', '?'),
    'T': ('\u1d40', '?'),
    'U': ('\u1d41', '?'),
    'V': ('\u2c7d', '?'),
    'W': ('\u1d42', '?'),
    'X': ('?', '?'),
    'Y': ('?', '?'),
    'Z': ('?', '?'),
    '+': ('\u207A', '\u208A'),
    '-': ('\u207B', '\u208B'),
    '=': ('\u207C', '\u208C'),
    '(': ('\u207D', '\u208D'),
    ')': ('\u207E', '\u208E'),
    ':alpha': ('\u1d45', '?'),
    ':beta': ('\u1d5d', '\u1d66'),
    ':gamma': ('\u1d5e', '\u1d67'),
    ':delta': ('\u1d5f', '?'),
    ':epsilon': ('\u1d4b', '?'),
    ':theta': ('\u1dbf', '?'),
    ':iota': ('\u1da5', '?'),
    ':pho': ('?', '\u1d68'),
    ':phi': ('\u1db2', '?'),
    ':psi': ('\u1d60', '\u1d69'),
    ':chi': ('\u1d61', '\u1d6a'),
    ':coffee': ('\u2615', '\u2615')
}

_analysis_funcs = [] # is used in register_all


def register_all():
    """Registers all analysis functions in the database.

    Use @analysis_function decorator to mark analysis functions
    in the code.

    :returns: number of registered analysis functions
    """
    from .models import AnalysisFunction
    for rf in _analysis_funcs:
        AnalysisFunction.objects.update_or_create(name=rf['name'],
                                                  pyfunc=rf['pyfunc'],
                                                  automatic=rf['automatic'])
    return len(_analysis_funcs)


def analysis_function(card_view_flavor="simple", name=None, automatic=False):
    """Decorator for marking a function as analysis function for a topography.

    :param card_view_flavor: defines how results for this function are displayed, see views.CARD_VIEW_FLAVORS
    :param name: human-readable name, default is to create this from function name
    :param automatic: choose True, if you want to calculate this for every new topography

    See views.py for possible view classes. The should be descendants of the class
    "SimpleCardView".
    """
    def register_decorator(func):
        """
        :param func: function to be registered, first arg must be a Topography
        :return: decorated function
        """

        if name is None:
            name_ = func.__name__.replace('_', ' ').title()
        else:
            name_ = name

        # the following data is used in "register_all" to create database objects for the function
        _analysis_funcs.append(dict(
            name = name_,
            pyfunc = func.__name__,
            automatic = automatic
        ))

        # TODO: Can a default argument be automated without writing it?
        # Add progress_recorder argument with default value, if not defined:
        # sig = signature(func)
        #if 'progress_recorder' not in sig.parameters:
        #    func = lambda *args, **kw: func(*args, progress_recorder=ConsoleProgressRecorder(), **kw)
        #    # the console progress recorder will work in tests and when calling the function
        #    # outside of an celery context
        #    #
        #    # When used in a celery context, this argument will be overwritten with
        #    # another recorder updated by a celery task

        func.card_view_flavor = card_view_flavor  # will be used when choosing the right view on request
        return func

    return register_decorator


def unicode_superscript(s):
    """
    Convert a string into the unicode superscript equivalent.

    :param s: Input string
    :return: String with superscript numerals
    """
    return ''.join(_unicode_map[c][0] if c in _unicode_map else c for c in s)


def unicode_subscript(s):
    """
    Convert numerals inside a string into the unicode subscript equivalent.

    :param s: Input string
    :return: String with superscript numerals
    """
    return ''.join(_unicode_map[c][1] if c in _unicode_map else c for c in s)


def float_to_unicode(f, digits=3):
    """
    Convert a floating point number into a human-readable unicode representation.
    Examples are: 1.2×10³, 120.43, 120×10⁻³. Exponents will be multiples of three.

    :param f: Floating-point number for conversion.
    :param digits: Number of significant digits.
    :return: Human-readable unicode string.
    """
    e = int(np.floor(np.log10(f)))
    m = f / 10 ** e

    e3 = (e // 3) * 3
    m *= 10 ** (e - e3)

    if e3 == 0:
        return ('{{:.{}g}}'.format(digits)).format(m)

    else:
        return ('{{:.{}g}}×10{{}}'.format(digits)).format(m, unicode_superscript(str(e3)))


def _reasonable_bins_argument(topography):
    """Returns a reasonable 'bins' argument for np.histogram for given topography's heights.

    :param topography: Line scan or topography from SurfaceTopography module
    :return: argument for 'bins' argument of np.histogram
    """
    if topography.is_uniform:
        return int(np.sqrt(np.prod(topography.nb_grid_pts)) + 1.0)
    else:
        return int(np.sqrt(np.prod(len(topography.positions()))) + 1.0) # TODO discuss whether auto or this
        # return 'auto'


def test_function(topography):
    return { 'name': 'Test result for test function called for topography {}.'.format(topography),
             'xunit': 'm',
             'yunit': 'm',
             'xlabel': 'x',
             'ylabel': 'y',
             'series': []}
test_function.card_view_flavor = 'simple'


class IncompatibleTopographyException(Exception):
    """Raise this exception in case a function cannot handle a topography.

    By handling this special exception, the UI can show the incompatibility
    as note to the user, not as failure. It is an excepted failure.
    """
    pass

#
# Use this during development if you need a long running task with failures
#
# @analysis_function(card_view_flavor='simple', automatic=True)
# def long_running_task(topography, progress_recorder=None, storage_prefix=None):
#     import time, random
#     n = 10 + random.randint(1,10)
#     F = 30
#     for i in range(n):
#         time.sleep(0.5)
#         if random.randint(1, F) == 1:
#             raise ValueError("This error is intended and happens with probability 1/{}.".format(F))
#         progress_recorder.set_progress(i+1, n)
#     return dict(message="done", physical_sizes=topography.physical_sizes, n=n)


@analysis_function(card_view_flavor='plot', automatic=True)
def height_distribution(topography, bins=None, wfac=5, progress_recorder=None, storage_prefix=None):

    if bins is None:
        bins = _reasonable_bins_argument(topography)

    profile = topography.heights()

    mean_height = np.mean(profile)
    rms_height = topography.rms_height(kind='Sq' if topography.dim == 2 else 'Rq')

    hist, bin_edges = np.histogram(np.ma.compressed(profile), bins=bins, density=True)

    minval = mean_height - wfac * rms_height
    maxval = mean_height + wfac * rms_height
    x_gauss = np.linspace(minval, maxval, 1001)
    y_gauss = np.exp(-(x_gauss - mean_height) ** 2 / (2 * rms_height ** 2)) / (np.sqrt(2 * np.pi) * rms_height)

    try:
        unit = topography.info['unit']
    except:
        unit = None

    return dict(
        name='Height distribution',
        scalars={
            'Mean Height': dict(value=mean_height, unit=unit),
            'RMS Height': dict(value=rms_height, unit=unit),
        },
        xlabel='Height',
        ylabel='Probability',
        xunit='' if unit is None else unit,
        yunit='' if unit is None else '{}⁻¹'.format(unit),
        series=[
            dict(name='Height distribution',
                 x=(bin_edges[:-1] + bin_edges[1:]) / 2,
                 y=hist,
                 ),
            dict(name='RMS height',
                 x=x_gauss,
                 y=y_gauss,
                 )
        ]
    )


def _moments_histogram_gaussian(arr, bins, wfac, quantity, label, unit, gaussian=True):
    """Return moments, histogram and gaussian for an array.

    :param arr: array
    :param bins: bins argument for np.histogram
    :param wfac: numeric width factor
    :param quantity: str, what kind of quantity this is (e.g. 'slope')
    :param label: str, how these results should be extra labeled (e.g. 'x direction')
    :param unit: str, unit of the quantity (e.g. '1/nm')
    :param gaussian: bool, if True, add gaussian
    :return: scalars, series

    The result can be used to extend the result dict of the analysis functions, e.g.

    result['scalars'].update(scalars)
    result['series'].extend(series)
    """

    arr = arr.flatten()

    mean = arr.mean()
    rms = np.sqrt((arr**2).mean())
    hist, bin_edges = np.histogram(arr, bins=bins, density=True)

    scalars = {
        f"Mean {quantity.capitalize()} ({label})": dict(value=mean, unit=unit),
        f"RMS {quantity.capitalize()} ({label})": dict(value=rms, unit=unit),
    }

    series = [
        dict(name=f'{quantity.capitalize()} distribution ({label})',
             x=(bin_edges[:-1] + bin_edges[1:]) / 2,
             y=hist)]

    if gaussian:
        minval = mean - wfac * rms
        maxval = mean + wfac * rms
        x_gauss = np.linspace(minval, maxval, 1001)
        y_gauss = np.exp(-(x_gauss - mean) ** 2 / (2 * rms ** 2)) / (np.sqrt(2 * np.pi) * rms)

        series.append(
            dict(name=f'RMS {quantity} ({label})',
             x=x_gauss,
             y=y_gauss)
        )

    return scalars, series


@analysis_function(card_view_flavor='plot', automatic=True)
def slope_distribution(topography, bins=None, wfac=5, progress_recorder=None, storage_prefix=None):

    if bins is None:
        bins = _reasonable_bins_argument(topography)

    result = dict(
        name='Slope distribution',
        xlabel='Slope',
        ylabel='Probability',
        xunit='1',
        yunit='1',
        scalars={},
        series=[]
    )
    # .. will be completed below..

    if topography.dim == 2:
        dh_dx, dh_dy = topography.derivative(n=1)

        #
        # Results for x direction
        #
        scalars_slope_x, series_slope_x = _moments_histogram_gaussian(dh_dx, bins=bins, wfac=wfac,
                                                                      quantity="slope", unit='1',
                                                                      label='x direction')
        result['scalars'].update(scalars_slope_x)
        result['series'].extend(series_slope_x)

        #
        # Results for x direction
        #
        scalars_slope_y, series_slope_y = _moments_histogram_gaussian(dh_dy, bins=bins, wfac=wfac,
                                                                      quantity="slope", unit='1',
                                                                      label='y direction')
        result['scalars'].update(scalars_slope_y)
        result['series'].extend(series_slope_y)

        #
        # Results for absolute gradient
        #
        # Not sure so far, how to calculate absolute gradient..
        #
        # absolute_gradients = np.sqrt(dh_dx**2+dh_dy**2)
        # scalars_grad, series_grad = _moments_histogram_gaussian(absolute_gradients, bins=bins, wfac=wfac,
        #                                                         quantity="slope", unit="?",
        #                                                         label='absolute gradient',
        #                                                         gaussian=False)
        # result['scalars'].update(scalars_grad)
        # result['series'].extend(series_grad)


    elif topography.dim == 1:
        dh_dx = topography.derivative(n=1)
        scalars_slope_x, series_slope_x = _moments_histogram_gaussian(dh_dx, bins=bins, wfac=wfac,
                                                                      quantity="slope", unit='1',
                                                                      label='x direction')
        result['scalars'].update(scalars_slope_x)
        result['series'].extend(series_slope_x)
    else:
        raise ValueError("This analysis function can only handle 1D or 2D topographies.")

    return result


@analysis_function(card_view_flavor='plot', automatic=True)
def curvature_distribution(topography, bins=None, wfac=5, progress_recorder=None, storage_prefix=None):
    if bins is None:
        bins = _reasonable_bins_argument(topography)

    #
    # Calculate the Laplacian
    #
    if topography.dim == 2:
        curv_x, curv_y = topography.derivative(n=2)
        if topography.is_periodic:
            curv = curv_x[:,:] + curv_y[:,:]
        else:
            curv = curv_x[:, 1:-1] + curv_y[1:-1, :]
    else:
        curv = topography.derivative(n=2)

    mean_curv = np.mean(curv)
    rms_curv = topography.rms_curvature()

    hist, bin_edges = np.histogram(np.ma.compressed(curv), bins=bins,
                                   density=True)

    minval = mean_curv - wfac * rms_curv
    maxval = mean_curv + wfac * rms_curv
    x_gauss = np.linspace(minval, maxval, 1001)
    y_gauss = np.exp(-(x_gauss - mean_curv) ** 2 / (2 * rms_curv ** 2)) / (np.sqrt(2 * np.pi) * rms_curv)

    unit = topography.info['unit']
    inverse_unit = '{}⁻¹'.format(unit)

    return dict(
        name='Curvature distribution',
        scalars={
            'Mean Curvature': dict(value=mean_curv, unit=inverse_unit),
            'RMS Curvature': dict(value=rms_curv, unit=inverse_unit),
        },
        xlabel='Curvature',
        ylabel='Probability',
        xunit=inverse_unit,
        yunit=unit,
        series=[
            dict(name='Curvature distribution',
                 x=(bin_edges[:-1] + bin_edges[1:]) / 2,
                 y=hist,
                 ),
            dict(name='RMS curvature',
                 x=x_gauss,
                 y=y_gauss,
                 )
        ]
    )


@analysis_function(card_view_flavor='plot', automatic=True)
def power_spectrum(topography, window=None, tip_radius=None, progress_recorder=None, storage_prefix=None):
    if window == 'None':
        window = None

    q_1D, C_1D = topography.power_spectrum_1D(window=window)
    # Remove NaNs and Infs
    q_1D = q_1D[np.isfinite(C_1D)]
    C_1D = C_1D[np.isfinite(C_1D)]

    unit = topography.info['unit']

    result = dict(
        name='Power-spectral density (PSD)',
        xlabel='Wavevector',
        ylabel='PSD',
        xunit='{}⁻¹'.format(unit),
        yunit='{}³'.format(unit),
        xscale='log',
        yscale='log',
        series=[
            dict(name='1D PSD along x',
                 x=q_1D[1:],
                 y=C_1D[1:],
                 ),
        ]
    )

    if topography.dim == 2:
        #
        # Add two more series with power spectra
        #
        sx, sy = topography.physical_sizes
        transposed_topography = Topography(topography.heights().T, (sy, sx))
        q_1D_T, C_1D_T = transposed_topography.power_spectrum_1D(window=window)
        q_2D, C_2D = topography.power_spectrum_2D(window=window,
                                                  nbins=len(q_1D) - 1)
        # Remove NaNs and Infs
        q_1D_T = q_1D_T[np.isfinite(C_1D_T)]
        C_1D_T = C_1D_T[np.isfinite(C_1D_T)]
        q_2D = q_2D[np.isfinite(C_2D)]
        C_2D = C_2D[np.isfinite(C_2D)]

        result['series'] = [
            dict(name='q/π × 2D PSD',
                 x=q_2D[1:],
                 y=q_2D[1:] * C_2D[1:] / np.pi,
                 ),
            result['series'][0],
            dict(name='1D PSD along y',
                 x=q_1D_T[1:],
                 y=C_1D_T[1:],
                 )
        ]

    return result


@analysis_function(card_view_flavor='plot', automatic=True)
def autocorrelation(topography, progress_recorder=None, storage_prefix=None):

    if topography.dim == 2:
        sx, sy = topography.physical_sizes
        transposed_topography = Topography(topography.heights().T, physical_sizes=(sy,sx), periodic=topography.is_periodic)
        r_T, A_T = transposed_topography.autocorrelation_1D()
        r_2D, A_2D = topography.autocorrelation_2D()

        # Truncate ACF at half the system size
        s = min(sx, sy) / 2
    else:
        s, = topography.physical_sizes

    if topography.is_uniform:
        r, A = topography.autocorrelation_1D()
    else:
        # Work around. The implementation for non-uniform line scans is very slow. Map onto a uniform grid.
        x, h = topography.positions_and_heights()
        min_dist = np.min(np.diff(x))
        if min_dist <= 0:
            raise RuntimeError('Positions not sorted')
        else:
            n = min(100000, 10 * int(s / min_dist))
        r, A = topography.to_uniform(n, 0).autocorrelation_1D()
        r = r[::10]
        A = A[::10]

    A = A[r < s]
    r = r[r < s]
    # Remove NaNs and Infs
    r = r[np.isfinite(A)]
    A = A[np.isfinite(A)]

    if topography.dim == 2:
        A_T = A_T[r_T < s]
        r_T = r_T[r_T < s]
        A_2D = A_2D[r_2D < s]
        r_2D = r_2D[r_2D < s]

        # Remove NaNs and Infs
        r_T = r_T[np.isfinite(A_T)]
        A_T = A_T[np.isfinite(A_T)]
        r_2D = r_2D[np.isfinite(A_2D)]
        A_2D = A_2D[np.isfinite(A_2D)]

    unit = topography.info['unit']

    #
    # Build series
    #
    series = [dict(name='Along x',
                 x=r,
                 y=A,
                )]

    if topography.dim == 2:
        series=[
            dict(name='Radial average',
                 x=r_2D,
                 y=A_2D,
                 ),
            series[0],
            dict(name='Along y',
                 x=r_T,
                 y=A_T,
                 )
        ]

    return dict(
        name='Height-difference autocorrelation function (ACF)',
        xlabel='Distance',
        ylabel='ACF',
        xunit=unit,
        yunit='{}²'.format(unit),
        xscale='log',
        yscale='log',
        series=series)


@analysis_function(card_view_flavor='plot', automatic=True)
def variable_bandwidth(topography, progress_recorder=None, storage_prefix=None):

    magnifications, bandwidths, rms_heights = topography.variable_bandwidth()

    unit = topography.info['unit']

    return dict(
        name='Variable-bandwidth analysis',
        xlabel='Bandwidth',
        ylabel='RMS Height',
        xunit=unit,
        yunit=unit,
        xscale='log',
        yscale='log',
        series=[
            dict(name='Variable-bandwidth analysis',
                 x=bandwidths,
                 y=rms_heights,
                 ),
        ]
    )


def _next_contact_step(system, history=None, pentol=None, maxiter=None):
    """
    Run a full contact calculation. Try to guess displacement such that areas
    are equally spaced on a log scale.

    Parameters
    ----------
    system : ContactMechanics.Systems.SystemBase
        The contact mechanical system.
    history : tuple
        History returned by past calls to next_step

    Returns
    -------
    displacements : numpy.ndarray
        Current surface displacement field.
    forces : numpy.ndarray
        Current surface pressure field.
    displacement : float
        Current displacement of the rigid surface
    load : float
        Current load.
    area : float
        Current fractional contact area.
    history : tuple
        History of contact calculations.
    """

    topography = system.surface
    substrate = system.substrate

    # Get the profile as a numpy array
    heights = topography.heights()

    # Find max, min and mean heights
    top = np.max(heights)
    middle = np.mean(heights)
    bot = np.min(heights)

    if history is None:
        step = 0
    else:
        mean_displacements, mean_gaps, mean_pressures, total_contact_areas, converged = history
        step = len(mean_displacements)

    if step == 0:
        mean_displacements = []
        mean_gaps = []
        mean_pressures = []
        total_contact_areas = []
        converged = np.array([], dtype=bool)

        mean_displacement = -middle
    elif step == 1:
        mean_displacement = -top + 0.01 * (top - middle)
    else:
        # Intermediate sort by area
        sorted_disp, sorted_area = np.transpose(sorted(zip(mean_displacements, total_contact_areas), key=lambda x:x[1]))

        ref_area = np.log10(np.array(sorted_area + 1 / np.prod(topography.nb_grid_pts)))
        darea = np.append(ref_area[1:] - ref_area[:-1], -ref_area[-1])
        i = np.argmax(darea)
        if i == step - 1:
            mean_displacement = bot + 2 * (sorted_disp[-1] - bot)
        else:
            mean_displacement = (sorted_disp[i] + sorted_disp[i + 1]) / 2

    opt = system.minimize_proxy(offset=mean_displacement, pentol=pentol, maxiter=maxiter)
    force_xy = opt.jac
    displacement_xy = opt.x[:force_xy.shape[0], :force_xy.shape[1]]
    mean_displacements = np.append(mean_displacements, [mean_displacement])
    mean_gaps = np.append(mean_gaps, [np.mean(displacement_xy) - middle - mean_displacement])
    mean_load = force_xy.sum() / np.prod(topography.physical_sizes)
    mean_pressures = np.append(mean_pressures, [mean_load])
    total_contact_area = (force_xy > 0).sum() / np.prod(topography.nb_grid_pts)
    total_contact_areas = np.append(total_contact_areas, [total_contact_area])
    converged = np.append(converged, np.array([opt.success], dtype=bool))

    area_per_pt = substrate.area_per_pt
    pressure_xy = force_xy / area_per_pt
    gap_xy = displacement_xy - topography.heights() - opt.offset
    gap_xy[gap_xy < 0.0] = 0.0

    contacting_points_xy = force_xy > 0

    return displacement_xy, gap_xy, pressure_xy, contacting_points_xy, \
           mean_displacement, mean_load, total_contact_area, \
           (mean_displacements, mean_gaps, mean_pressures, total_contact_areas, converged)


def _contact_at_given_load(system, external_force, history=None, pentol=None, maxiter=None):
    """
    Run a full contact calculation at a given external load.

    Parameters
    ----------
    system : ContactMechanics.Systems.SystemBase
        The contact mechanical system.
    external_force : float
        The force pushing the surfaces together.
    history : tuple
        History returned by past calls to next_step

    Returns
    -------
    displacements : numpy.ndarray
        Current surface displacement field.
    forces : numpy.ndarray
        Current surface pressure field.
    displacement : float
        Current displacement of the rigid surface
    load : float
        Current load.
    area : float
        Current fractional contact area.
    history : tuple
        History of contact calculations.
    """

    topography = system.surface
    substrate = system.substrate

    # Get the profile as a numpy array
    heights = topography.heights()

    # Find max, min and mean heights
    top = np.max(heights)
    middle = np.mean(heights)
    bot = np.min(heights)

    if history is None:
        mean_displacements = []
        mean_gaps = []
        mean_pressures = []
        total_contact_areas = []
        converged = np.array([], dtype=bool)
    if history is not None:
        mean_displacements, mean_gaps, mean_pressures, total_contact_areas, converged = history

    opt = system.minimize_proxy(external_force=external_force, pentol=pentol, maxiter=maxiter)
    force_xy = opt.jac
    displacement_xy = opt.x[:force_xy.shape[0], :force_xy.shape[1]]
    mean_displacements = np.append(mean_displacements, [opt.offset])
    mean_gaps = np.append(mean_gaps, [np.mean(displacement_xy) - middle - opt.offset])
    mean_load = force_xy.sum() / np.prod(topography.physical_sizes)
    mean_pressures = np.append(mean_pressures, [mean_load])
    total_contact_area = (force_xy > 0).sum() / np.prod(topography.nb_grid_pts)
    total_contact_areas = np.append(total_contact_areas, [total_contact_area])
    converged = np.append(converged, np.array([opt.success], dtype=bool))

    area_per_pt = substrate.area_per_pt
    pressure_xy = force_xy / area_per_pt
    gap_xy = displacement_xy - topography.heights() - opt.offset
    gap_xy[gap_xy < 0.0] = 0.0

    contacting_points_xy = force_xy > 0

    return displacement_xy, gap_xy, pressure_xy, contacting_points_xy, \
           opt.offset, mean_load, total_contact_area, \
           (mean_displacements, mean_gaps, mean_pressures, total_contact_areas, converged)


@analysis_function(card_view_flavor='contact mechanics', automatic=True)
def contact_mechanics(topography, substrate_str=None, hardness=None, nsteps=10,
                      pressures=None, maxiter=100, progress_recorder=None, storage_prefix=None):
    """
    Note that `loads` is a list of pressures if the substrate is periodic and a list of forces otherwise.

    :param topography:
    :param substrate_str: one of ['periodic', 'nonperiodic', None ]; if None, choose from topography's 'is_periodic' flag
    :param hardness: float value (unit: E*)
    :param nsteps: int or None, if None, "loads" must be given a list
    :param pressures: list of floats or None, if None, choose pressures automatically by using given number of steps (nsteps)
    :param maxiter: int, maximum number of iterations unless convergence
    :param progress_recorder:
    :param storage_prefix:
    :return:
    """

    if topography.dim == 1:
        raise IncompatibleTopographyException("Contact mechanics not implemented for line scans.")

    #
    # Choose substrate str from 'is_periodic' flag, if not given
    #
    if substrate_str is None:
        substrate_str = 'periodic' if topography.is_periodic else 'nonperiodic'

    #
    # Check whether either loads or nsteps is given, but not both
    #
    if (nsteps is None) and (pressures is None):
        raise ValueError("Either 'nsteps' or 'pressures' must be given for contact mechanics calculation.")

    if (nsteps is not None) and (pressures is not None):
        raise ValueError("Both 'nsteps' and 'pressures' are given. One must be None.")

    #
    # Check some limits for number of pressures, maxiter, and nsteps
    # (same should be used in HTML page and checked by JS)
    #
    if (nsteps) and ((nsteps<CONTACT_MECHANICS_KWARGS_LIMITS['nsteps']['min']) or (nsteps>CONTACT_MECHANICS_KWARGS_LIMITS['nsteps']['max'])):
        raise ValueError(f"Invalid value for 'nsteps': {nsteps}")
    if (pressures) and ((len(pressures)<1) or (len(pressures)>CONTACT_MECHANICS_KWARGS_LIMITS['pressures']['maxlen'])):
        raise ValueError(f"Invalid number of pressures given: {len(pressures)}")
    if (maxiter<CONTACT_MECHANICS_KWARGS_LIMITS['maxiter']['min']) or (maxiter>CONTACT_MECHANICS_KWARGS_LIMITS['maxiter']['max']):
        raise ValueError(f"Invalid value for 'maxiter': {maxiter}")

    # Conversion of force units
    force_conv = np.prod(topography.physical_sizes)

    #
    # Some constants
    #
    min_pentol = 1e-12  # lower bound for the penetration tolerance

    if (hardness is not None) and (hardness > 0):
        topography = PlasticTopography(topography, hardness)

    half_space_factory = dict(periodic=PeriodicFFTElasticHalfSpace,
                              nonperiodic=FreeFFTElasticHalfSpace)

    half_space_kwargs = {}
    if substrate_str == 'nonperiodic':
        half_space_kwargs['check_boundaries'] = False # TODO remove this with PyCo > 0.52.0, there the default is changed

    substrate = half_space_factory[substrate_str](topography.nb_grid_pts, 1.0, topography.physical_sizes,
                                                  **half_space_kwargs)

    system = make_system(substrate, topography)

    # Heuristics for the possible tolerance on penetration.
    # This is necessary because numbers can vary greatly
    # depending on the system of units.
    rms_height = topography.rms_height()
    pentol = rms_height / (10 * np.mean(topography.nb_grid_pts))
    pentol = max(pentol, min_pentol)

    netcdf_format = 'NETCDF4'

    data_paths = [] # collect in _next_contact_step?

    if pressures is not None:
        nsteps = len(pressures)

    history = None
    for i in range(nsteps):
        if pressures is None:
            displacement_xy, gap_xy, pressure_xy, contacting_points_xy, \
                mean_displacement, mean_pressure, total_contact_area, history = \
                _next_contact_step(system, history=history, pentol=pentol, maxiter=maxiter)
        else:
            displacement_xy, gap_xy, pressure_xy, contacting_points_xy, \
                mean_displacement, mean_pressure, total_contact_area, history = \
                _contact_at_given_load(system, pressures[i]*force_conv, history=history, pentol=pentol, maxiter=maxiter)

        #
        # Save displacement_xy, gap_xy, pressure_xy and contacting_points_xy
        # to storage, will be retrieved later for visualization
        #
        pressure_xy = xr.DataArray(pressure_xy, dims=('x', 'y')) # maybe define coordinates
        gap_xy = xr.DataArray(gap_xy, dims=('x', 'y'))
        displacement_xy = xr.DataArray(displacement_xy, dims=('x', 'y'))
        contacting_points_xy = xr.DataArray(contacting_points_xy, dims=('x', 'y'))

        dataset = xr.Dataset({'pressure': pressure_xy,
                              'contacting_points': contacting_points_xy,
                              'gap': gap_xy,
                              'displacement': displacement_xy}) # one dataset per analysis step: smallest unit to retrieve
        dataset.attrs['mean_pressure'] = mean_pressure
        dataset.attrs['total_contact_area'] = total_contact_area
        dataset.attrs['type'] = substrate_str
        if hardness:
            dataset.attrs['hardness'] = hardness # TODO how to save hardness=None? Not possible in netCDF

        with tempfile.NamedTemporaryFile(prefix='analysis-') as tmpfile:
            dataset.to_netcdf(tmpfile.name, format=netcdf_format)

            storage_path = storage_prefix+"result-step-{}.nc".format(i)
            tmpfile.seek(0)
            storage_path = default_storage.save(storage_path, File(tmpfile))
            data_paths.append(storage_path)

        progress_recorder.set_progress(i + 1, nsteps)

    mean_displacement, mean_gap, mean_pressure, total_contact_area, converged = history

    mean_pressure = np.array(mean_pressure)
    total_contact_area = np.array(total_contact_area)
    mean_displacement = np.array(mean_displacement)
    mean_gap = np.array(mean_gap)
    converged = np.array(converged)

    data_paths = np.array(data_paths, dtype='str')
    sort_order = np.argsort(mean_pressure)

    return dict(
        name='Contact mechanics',
        area_per_pt=substrate.area_per_pt,
        maxiter=maxiter,
        min_pentol=min_pentol,
        mean_pressures=mean_pressure[sort_order],
        total_contact_areas=total_contact_area[sort_order],
        mean_displacements=mean_displacement[sort_order]/rms_height,
        mean_gaps=mean_gap[sort_order]/rms_height,
        converged=converged[sort_order],
        data_paths=data_paths[sort_order],
        effective_kwargs = dict(
            substrate_str=substrate_str,
            hardness=hardness,
            nsteps=nsteps,
            pressures=pressures,
            maxiter=maxiter,
        )
    )


@analysis_function(card_view_flavor='rms table', automatic=True, name="RMS Values")
def rms_values(topography, progress_recorder=None, storage_prefix=None):
    """Just calculate RMS values for given topography.

    Parameters
    ----------
    topography
    progress_recorder
    storage_prefix

    Returns
    -------
    list of dicts where each dict has keys

     quantity
     direction
     value
     unit
    """

    try:
        unit = topography.info['unit']
        inverse_unit = '{}⁻¹'.format(unit)
    except:
        unit = None
        inverse_unit = None

    def rms_slope_from_der(der):
        der = der.flatten()
        return np.sqrt(((der**2).mean()))

    result = [
        {
            'quantity': 'RMS Height',
            'direction': None,
            'value': topography.rms_height(),
            'unit': unit,
        },
        {
            'quantity': 'RMS Curvature',
            'direction': None,
            'value': topography.rms_curvature(),
            'unit': inverse_unit,
        },
    ]

    if topography.dim == 2:
        dh_dx, dh_dy = topography.derivative(n=1)
        result.extend([
            {
                'quantity': 'RMS Slope',
                'direction': 'x',
                'value': rms_slope_from_der(dh_dx),
                'unit': 1,
            },
            {
                'quantity': 'RMS Slope',
                'direction': 'y',
                'value': rms_slope_from_der(dh_dy),
                'unit': 1,
            }
        ])
    elif topography.dim == 1:
        dh_dx = topography.derivative(n=1)
        result.extend([
            {
                'quantity': 'RMS Slope',
                'direction': 'x',
                'value': rms_slope_from_der(dh_dx),
                'unit': 1,
            }
        ])
    else:
        raise ValueError("This analysis function can only handle 1D or 2D topographies.")

    return result
