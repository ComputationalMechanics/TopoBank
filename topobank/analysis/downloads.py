from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.core.files.storage import default_storage

import pandas as pd
import io
import pickle
import numpy as np
import zipfile
import os.path
import textwrap

from .models import Analysis
from .views import CARD_VIEW_FLAVORS
from .utils import mangle_sheet_name

#######################################################################
# Download views
#######################################################################


def download_analyses(request, ids, card_view_flavor, file_format):
    """Returns a file comprised from analyses results.

    :param request:
    :param ids: comma separated string with analyses ids
    :param card_view_flavor: card view flavor, see CARD_VIEW_FLAVORS
    :param file_format: requested file format
    :return:
    """

    #
    # Check permissions and collect analyses
    #
    user = request.user
    if not user.is_authenticated:
        return HttpResponseForbidden()

    analyses_ids = [int(i) for i in ids.split(',')]

    analyses = []

    for aid in analyses_ids:
        analysis = Analysis.objects.get(id=aid)

        #
        # Check whether user has view permission for requested analysis
        #
        if not user.has_perm("view_surface", analysis.topography.surface):
            return HttpResponseForbidden()

        analyses.append(analysis)

    #
    # Check flavor and format argument
    #
    card_view_flavor = card_view_flavor.replace('_', ' ')  # may be given with underscore in URL
    if not card_view_flavor in CARD_VIEW_FLAVORS:
        return HttpResponseBadRequest("Unknown card view flavor '{}'.".format(card_view_flavor))

    download_response_functions = {
        ('plot', 'xlsx'): download_plot_analyses_to_xlsx,
        ('plot', 'txt'): download_plot_analyses_to_txt,
        ('rms table', 'xlsx'): download_rms_table_analyses_to_xlsx,
        ('rms table', 'txt'): download_rms_table_analyses_to_txt,
        ('contact mechanics', 'zip'): download_contact_mechanics_analyses_as_zip,
    }

    #
    # Dispatch
    #
    key = (card_view_flavor, file_format)
    if key not in download_response_functions:
        return HttpResponseBadRequest(
            "Cannot provide a download for card view flavor {} in file format ".format(card_view_flavor))

    return download_response_functions[key](request, analyses)


def _analyses_meta_data_dataframe(analyses, request):
    """Generates a pandas.DataFrame with meta data about analyses.

    Parameters
    ----------
    analyses:
        sequence of Analysis instances
    request:
        current request

    Returns
    -------
    pandas.DataFrame, can be inserted as extra sheet
    """

    properties = []
    values = []
    for i, analysis in enumerate(analyses):

        pub = analysis.topography.surface.publication if analysis.topography.surface.is_published else None

        if i == 0:
            properties = ["Function"]
            values = [str(analysis.function)]

        properties += ['Topography', 'Creator',
                       'Further arguments of analysis function', 'Start time of analysis task',
                       'End time of analysis task', 'Duration of analysis task']

        values += [str(analysis.topography.name), str(analysis.topography.creator),
                   analysis.get_kwargs_display(), str(analysis.start_time),
                   str(analysis.end_time), str(analysis.duration())]

        if analysis.configuration is None:
            properties.append("Versions of dependencies")
            values.append("Unknown. Please recalculate this analysis in order to have version information here.")
        else:
            versions_used = analysis.configuration.versions.order_by('dependency__import_name')

            for version in versions_used:
                properties.append(f"Version of '{version.dependency.import_name}'")
                values.append(f"{version.number_as_string()}")

        if pub:
            # If the surface of the topography was published, the URL is inserted
            properties.append("Publication URL (surface data)")
            values.append(request.build_absolute_uri(pub.get_absolute_url()))

        # We want an empty line on the properties sheet in order to distinguish the topographies
        properties.append("")
        values.append("")

    df = pd.DataFrame({'Property': properties, 'Value': values})

    return df


def _publications_urls(request, analyses):
    """Return set of publication URLS for given analyses.

    Parameters
    ----------
    request
        HTTPRequest
    analyses
        seq of Analysis instances
    Returns
    -------
    Set of absolute URLs (strings)
    """
    # Collect publication links, if any
    publication_urls = set()
    for a in analyses:
        if a.topography.surface.is_published:
            pub = a.topography.surface.publication
            pub_url = request.build_absolute_uri(pub.get_absolute_url())
            publication_urls.add(pub_url)
    return publication_urls


def _analysis_header_for_txt_file(analysis, as_comment=True):
    """

    Parameters
    ----------
    analysis
        Analysis instance
    as_comment
        boolean, if True, add '# ' in front of each line

    Returns
    -------
    str
    """

    topography = analysis.topography
    topo_creator = topography.creator

    s = 'Topography: {}\n'.format(topography.name) +\
        '{}\n'.format('=' * (len('Topography: ') + len(str(topography.name)))) +\
        'Creator: {}\n'.format(topo_creator) +\
        'Further arguments of analysis function: {}\n'.format(analysis.get_kwargs_display()) +\
        'Start time of analysis task: {}\n'.format(analysis.start_time) +\
        'End time of analysis task: {}\n'.format(analysis.end_time) +\
        'Duration of analysis task: {}\n'.format(analysis.duration())
    if analysis.configuration is None:
        s += 'Versions of dependencies (like "SurfaceTopography") are unknown for this analysis.\n'
        s += 'Please recalculate in order to have version information here.\n'
    else:
        versions_used = analysis.configuration.versions.order_by('dependency__import_name')

        for version in versions_used:
            s += f"Version of '{version.dependency.import_name}': {version.number_as_string()}\n"
    s += '\n'

    if as_comment:
        s = textwrap.indent(s, '# ', predicate=lambda s: True)  # prepend to all lines, also empty

    return s


def download_plot_analyses_to_txt(request, analyses):
    """Download plot data for given analyses as CSV file.

        Parameters
        ----------
        request
            HTTPRequest
        analyses
            Sequence of Analysis instances

        Returns
        -------
        HTTPResponse
    """
    # TODO: It would probably be useful to use the (some?) template engine for this.
    # TODO: We need a mechanism for embedding references to papers into output.

    # Collect publication links, if any
    publication_urls = _publications_urls(request, analyses)

    # Pack analysis results into a single text file.
    f = io.StringIO()
    for i, analysis in enumerate(analyses):
        if i == 0:
            f.write('# {}\n'.format(analysis.function) +
                    '# {}\n'.format('=' * len(str(analysis.function))))

            f.write('# IF YOU USE THIS DATA IN A PUBLICATION, PLEASE CITE XXX.\n' +
                    '\n')
            if len(publication_urls) > 0:
                f.write('#\n')
                f.write('# For these analyses, published data was used. Please visit these URLs for details:\n')
                for pub_url in publication_urls:
                    f.write(f'# - {pub_url}\n')
                f.write('#\n')

        f.write(_analysis_header_for_txt_file(analysis))

        result = pickle.loads(analysis.result)
        xunit_str = '' if result['xunit'] is None else ' ({})'.format(result['xunit'])
        yunit_str = '' if result['yunit'] is None else ' ({})'.format(result['yunit'])
        header = 'Columns: {}{}, {}{}'.format(result['xlabel'], xunit_str, result['ylabel'], yunit_str)

        for series in result['series']:
            np.savetxt(f, np.transpose([series['x'], series['y']]),
                       header='{}\n{}\n{}'.format(series['name'], '-' * len(series['name']), header))
            f.write('\n')

    # Prepare response object.
    response = HttpResponse(f.getvalue(), content_type='application/text')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format('{}.txt'.format(analysis.function.pyfunc))

    # Close file and return response.
    f.close()
    return response


def download_plot_analyses_to_xlsx(request, analyses):
    """Download plot data for given analyses as XLSX file.

    Parameters
    ----------
    request
        HTTPRequest
    analyses
        Sequence of Analysis instances

    Returns
    -------
    HTTPResponse
    """
    # TODO: We need a mechanism for embedding references to papers into output.

    # Pack analysis results into a single text file.
    f = io.BytesIO()
    excel = pd.ExcelWriter(f)

    # Analyze topography names and store a distinct name
    # which can be used in sheet names if topography names are not unique
    topography_names_in_sheet_names = [a.topography.name for a in analyses]

    for tn in set(topography_names_in_sheet_names):  # iterate over distinct names

        # replace name with a unique one using a counter
        indices = [i for i, a in enumerate(analyses) if a.topography.name == tn]

        if len(indices) > 1:  # only rename if not unique
            for k, idx in enumerate(indices):
                topography_names_in_sheet_names[idx] += f" ({k + 1})"

    for i, analysis in enumerate(analyses):
        result = pickle.loads(analysis.result)
        column1 = '{} ({})'.format(result['xlabel'], result['xunit'])
        column2 = '{} ({})'.format(result['ylabel'], result['yunit'])

        # determine name of topography in sheet name
        for series in result['series']:
            df = pd.DataFrame({column1: series['x'], column2: series['y']})

            sheet_name = '{} - {}'.format(topography_names_in_sheet_names[i],
                                          series['name']).replace('/', ' div ')
            df.to_excel(excel, sheet_name=mangle_sheet_name(sheet_name))
    df = _analyses_meta_data_dataframe(analyses, request)
    df.to_excel(excel, sheet_name='INFORMATION', index=False)
    excel.close()

    # Prepare response object.
    response = HttpResponse(f.getvalue(),
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format('{}.xlsx'.format(analysis.function.pyfunc))

    # Close file and return response.
    f.close()
    return response


def download_rms_table_analyses_to_txt(request, analyses):
    """Download RMS table data for given analyses as CSV file.

        Parameters
        ----------
        request
            HTTPRequest
        analyses
            Sequence of Analysis instances

        Returns
        -------
        HTTPResponse
    """
    # TODO: It would probably be useful to use the (some?) template engine for this.
    # TODO: We need a mechanism for embedding references to papers into output.

    # Collect publication links, if any
    publication_urls = _publications_urls(request, analyses)

    # Pack analysis results into a single text file.
    data = []
    f = io.StringIO()
    for i, analysis in enumerate(analyses):
        if i == 0:
            f.write('# {}\n'.format(analysis.function) +
                    '# {}\n'.format('=' * len(str(analysis.function))))

            f.write('# IF YOU USE THIS DATA IN A PUBLICATION, PLEASE CITE XXX.\n' +
                    '#\n')
            if len(publication_urls) > 0:
                f.write('#\n')
                f.write('# For these analyses, published data was used. Please visit these URLs for details:\n')
                for pub_url in publication_urls:
                    f.write(f'# - {pub_url}\n')
                f.write('#\n')

        f.write(_analysis_header_for_txt_file(analysis))

        result = pickle.loads(analysis.result)
        topography = analysis.topography
        for row in result:
            data.append([topography.surface.name,
                         topography.name,
                         row['quantity'],
                         row['direction'] if row['direction'] else '',
                         row['value'],
                         row['unit']])

    f.write('# Table of RMS Values\n')
    df = pd.DataFrame(data, columns=['surface','topography', 'quantity', 'direction', 'value', 'unit'])
    df.to_csv(f, index=False)
    f.write('\n')

    # Prepare response object.
    response = HttpResponse(f.getvalue(), content_type='application/text')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format('{}.txt'.format(analysis.function.pyfunc))

    # Close file and return response.
    f.close()
    return response


def download_rms_table_analyses_to_xlsx(request, analyses):
    """Download RMS table data for given analyses as XLSX file.

        Parameters
        ----------
        request
            HTTPRequest
        analyses
            Sequence of Analysis instances

        Returns
        -------
        HTTPResponse
        """
    f = io.BytesIO()
    excel = pd.ExcelWriter(f)

    data = []
    for analysis in analyses:
        topo = analysis.topography
        for row in pickle.loads(analysis.result):
            row['surface'] = topo.surface.name
            row['topography'] = topo.name
            data.append(row)

    rms_df = pd.DataFrame(data, columns=['surface', 'topography', 'quantity', 'direction', 'value', 'unit'])
    rms_df.to_excel(excel, sheet_name="RMS values", index=False)
    info_df = _analyses_meta_data_dataframe(analyses, request)
    info_df.to_excel(excel, sheet_name='INFORMATION', index=False)
    excel.close()

    # Prepare response object.
    response = HttpResponse(f.getvalue(),
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="rms_table.xlsx"'

    # Close file and return response.
    f.close()
    return response


def download_contact_mechanics_analyses_as_zip(request, analyses):
    """Provides a ZIP file with contact mechanics data.

    :param request: HTTPRequest
    :param analyses: sequence of Analysis instances
    :return: HTTP Response with file download
    """

    bytes = io.BytesIO()

    zf = zipfile.ZipFile(bytes, mode='w')

    #
    # Add directories and files for all analyses
    #
    zip_dirs = set()

    for analysis in analyses:

        zip_dir = analysis.topography.name
        if zip_dir in zip_dirs:
            # make directory unique
            zip_dir += "-{}".format(analysis.topography.id)
        zip_dirs.add(zip_dir)

        #
        # Add a csv file with plot data
        #
        analysis_result = analysis.result_obj

        col_keys = ['mean_pressures', 'total_contact_areas', 'mean_gaps', 'converged', 'data_paths']
        col_names = ["Normalized pressure p/E*", "Fractional contact area A/A0", "Normalized mean gap u/h_rms",
                     "converged", "filename"]

        col_dicts = {col_names[i]:analysis_result[k] for i,k in enumerate(col_keys)}
        plot_df = pd.DataFrame(col_dicts)
        plot_df['filename'] = plot_df['filename'].map(lambda fn: os.path.split(fn)[1])  # only simple filename

        plot_filename_in_zip = os.path.join(zip_dir, 'plot.csv')
        zf.writestr(plot_filename_in_zip, plot_df.to_csv())

        #
        # Add all files from storage
        #
        prefix = analysis.storage_prefix

        directories, filenames = default_storage.listdir(prefix)

        for file_no, fname in enumerate(filenames):

            input_file = default_storage.open(prefix + fname)

            filename_in_zip = os.path.join(zip_dir, fname)

            try:
                zf.writestr(filename_in_zip, input_file.read())
            except Exception as exc:
                zf.writestr("errors-{}.txt".format(file_no),
                            "Cannot save file {} in ZIP, reason: {}".format(filename_in_zip, str(exc)))

        #
        # Add a file with version information
        #
        zf.writestr(os.path.join(zip_dir, 'info.txt'),
                    _analysis_header_for_txt_file(analysis))


    #
    # Add a Readme file
    #
    zf.writestr("README.txt",\
                f"""
Contents of this ZIP archive
============================
This archive contains data from contact mechanics calculation.

Each directory corresponds to one topography and is named after the topography.
Inside you find two types of files:

- a simple CSV file ('plot.csv')
- a couple of classical netCDF files (Extension '.nc')

The file 'plot.csv' contains a table with the data used in the plot,
one line for each calculation step. It has the following columns:

- Zero-based index column
- Normalized pressure in units of p/E*
- Fractional contact area in units of A/A0
- Normalized mean gap in units of u/h_rms
- A boolean flag (True/False) which indicates whether the calculation converged
  within the given limit
- Filename of the NetCDF file (order of filenames may be different than index)

So each line also refers to one NetCDF file in the directory, it corresponds to
one external pressure. Inside the NetCDF file you'll find the variables

* `contact_points`: boolean array, true if point is in contact
* `pressure`: floating-point array containing local pressure (in units of `E*`)
* `gap`: floating-point array containing the local gap
* `displacement`: floating-point array containing the local displacements

as well as the attributes

* `mean_pressure`: mean pressure (in units of `E*`)
* `total_contact_area`: total contact area (fractional)

In order to read the data, you can use a netCDF library.
Here are some examples:

Accessing the NetCDF files
==========================

### Python

Given the package [`netcdf4-python`](http://netcdf4-python.googlecode.com/) is installed:

```
import netCDF4
ds = netCDF4.Dataset("result-step-0.nc")
print(ds)
pressure = ds['pressure'][:]
mean_pressure = ds.mean_pressure
```

Another convenient package you can use is [`xarray`](xarray.pydata.org/).

### Matlab

In order to read the pressure map in Matlab, use

```
ncid = netcdf.open("result-step-0.nc",'NC_NOWRITE');
varid = netcdf.inqVarID(ncid,"pressure");
pressure = netcdf.getVar(ncid,varid);
```

Have look in the official Matlab documentation for more information.

Version information
===================

For version information of the packages used, please look into the files named
'info.txt' in the subdirectories for each topography. The versions of the packages
used for analysis may differ among topographies, because they may have been
calculated at different times.
    """)

    zf.close()

    # Prepare response object.
    response = HttpResponse(bytes.getvalue(),
                            content_type='application/x-zip-compressed')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format('contact_mechanics.zip')

    return response
