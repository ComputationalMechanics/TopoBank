/* Project specific Javascript goes here. */

/*
Formatting hack to get around crispy-forms unfortunate hardcoding
in helpers.FormHelper:

    if template_pack == 'bootstrap4':
        grid_colum_matcher = re.compile('\w*col-(xs|sm|md|lg|xl)-\d+\w*')
        using_grid_layout = (grid_colum_matcher.match(self.label_class) or
                             grid_colum_matcher.match(self.field_class))
        if using_grid_layout:
            items['using_grid_layout'] = True

Issues with the above approach:

1. Fragile: Assumes Bootstrap 4's API doesn't change (it does)
2. Unforgiving: Doesn't allow for any variation in template design
3. Really Unforgiving: No way to override this behavior
4. Undocumented: No mention in the documentation, or it's too hard for me to find
*/
$('.form-group').removeClass('row');

/**
 * Create a plottable plot with surface summary
 *
 * @param {String} DOM id of <div> element in which the plot is inserted
 * @param {Object} list with bandwidth data for topographies
 *
 * Each element needs the keys
 *
 * upper_bound: number in meters
 * lower_bound: number in meters
 * name: topography name
 * link: link which should be followed, when clicked
 */
function surface_summary_plot(element, bandwidths_data) {

    // var colorScale = new Plottable.Scales.Color();
    var activeBarColor = "#007bff";
    var inactiveBarColor = "#7c7c7d";

    var xScale = new Plottable.Scales.Log();
    var xAxisFormatter = new Plottable.Formatters.siSuffix(2)
    var xAxis = new Plottable.Axes.Numeric(xScale, "bottom").formatter(xAxisFormatter);
    var xAxisLabel = new Plottable.Components.Label("Bandwidth (m)");

    var yScale = new Plottable.Scales.Category();

    //
    // Create rectangles
    //
    var plot = new Plottable.Plots.Rectangle()
      .x(function (d) {
        return d.lower_bound;
      }, xScale)
      .x2(function (d) {
        return d.upper_bound;
      })
      .y(function (d) {
        return d.name;
      }, yScale)
      .label(function (d) {
        return d.name;
      })
      .labelsEnabled(true)
      .attr("fill", inactiveBarColor)
      .addDataset(new Plottable.Dataset(bandwidths_data));

    //
    // Click on bar should redirect to topography detail
    //
    var click_interaction = new Plottable.Interactions.Click();
    click_interaction.onClick(function (point) {
      // follow the link which was set in the data of the element
      var selection = plot.entitiesAt(point)[0].selection;
      window.location = selection.data()[0].link;
    });
    click_interaction.attachTo(plot);

    //
    // Adjust color of bar when moving over
    //
    var move_interaction = new Plottable.Interactions.Pointer();
    move_interaction.onPointerMove(function(p) {
      plot.entities().forEach(function(entity) {
        entity.selection.attr("fill", inactiveBarColor);
      });
      var entities = plot.entitiesAt(p);
      if (entities.length > 0) {
          entities[0].selection.attr("fill", activeBarColor);
      }
    });
    move_interaction.attachTo(plot);

    //
    // Arrange components and render
    //
    var chart = new Plottable.Components.Table([
      [plot],
      [xAxis],
      [xAxisLabel]
    ]);

    chart.renderTo(element);

    window.addEventListener("resize", function () {
      chart.redraw();
    });

}

function verifyPrecision(precision) {
    if (precision < 0 || precision > 20) {
        throw new RangeError("Formatter precision must be between 0 and 20");
    }
    if (precision !== Math.floor(precision)) {
        throw new RangeError("Formatter precision must be an integer");
    }
}

/*
 * Convert numerals inside a string into the unicode superscript equivalent, e.g.
 *   µm3 => µm³
 */
function unicode_superscript(s) {
    superscript_dict = {
        '0': '⁰',
        '1': '¹',
        '2': '²',
        '3': '³',
        '4': '⁴',
        '5': '⁵',
        '6': '⁶',
        '7': '⁷',
        '8': '⁸',
        '9': '⁹',
        '+': '⁺',
        '-': '⁻',
        '.': '⋅',
    };
    return s.split('').map(c => c in superscript_dict ? superscript_dict[c] : c).join('');
}


/**
 * Creates a formatter that formats numbers to show no more than
 * [maxNumberOfDecimalPlaces] decimal places in exponential notation.
 * Exponentials will be displayed human readably, i.e. 1.3×10³.
 *
 * @param {number} [d] The number to be formatted
 * @param {number} [maxNumberOfDecimalPlaces] The number of decimal places to show (default 3).
 *
 * @returns {Formatter} A formatter for general values.
 */
function format_exponential(d, maxNumberOfDecimalPlaces) {
        if (maxNumberOfDecimalPlaces === void 0) { maxNumberOfDecimalPlaces = 3; }

        if (d == 0 || d === undefined || isNaN(d) || Math.abs(d) == Infinity) {
            return String(d);
        }
        else if (typeof d === "number") {
            var multiplier = Math.pow(10, maxNumberOfDecimalPlaces);
            var sign = d < 0 ? -1 : 1;
            var e = Math.floor(Math.log(sign * d) / Math.log(10));
            var m = sign * d / Math.pow(10, e);
            var m_rounded = Math.round(m * multiplier) / multiplier;
            if (m_rounded == 10) {
                m_rounded = 1;
                e++;
            }
            if (e == 0) {
                return String(sign * m_rounded); // do not attach ×10⁰ == 1
            }
            else if (m_rounded == 1) {
                if (sign > 0) {
                    return "10" + unicode_superscript(String(e));
                }
                else {
                    return "-10" + unicode_superscript(String(e));
                }
            }
            else {
                return String(sign * m_rounded) + "×10" + unicode_superscript(String(e));
            }
        }
        else {
            return String(d);
        }
}

/**
 * Submit an ajax call for updating an card in the analysis view.
 *
 * @param card_url {String} URL to call in order to get card content as HTTP response
 * @param card_element_id {String} CSS id of the div element containing the card
 * @param template_flavor {String} defines which template should be finally used (e.g. 'list', 'detail')
 * @param function_id {Number} Integer number of the analysis function which should be displayed
 * @param topography_ids {Object} list of integer numbers with ids of topographies which should be displayed
 * @param first_call {Boolean} true if this is the first call in a chain of ajax calls
 */
function submit_analyses_card_ajax(card_url, card_element_id, template_flavor, function_id, topography_ids, first_call) {

      var jquery_card_selector = "#"+card_element_id;

      $.ajax({
        type: "GET",
        url: card_url,
        timeout: 0,
        data: {
           card_id: card_element_id,
           template_flavor: template_flavor,
           function_id: function_id,
           topography_ids: topography_ids
        },
        success : function(data, textStatus, xhr) {
          // console.log("Received response for card '"+card_element_id+"'. Status: "+xhr.status)
          if (first_call) {
            $(jquery_card_selector).html(data); // insert resulting HTML code
          }
          if (xhr.status==202) {
            // Data is not ready, retrigger AJAX call
            console.log("Analyses for card with element id '"+card_element_id+"' not ready. Retrying..");
            setTimeout(function () {
              submit_analyses_card_ajax(card_url, card_element_id, template_flavor, function_id, topography_ids, false);
            }, 1000); // TODO limit number of retries?
          } else {
            $(jquery_card_selector).html(data); // insert resulting HTML code
          }
        },
        error: function(xhr, textStatus, errorThrown) {
          // console.log("Error receiving response for card '"+card_element_id+"'. Status: "+xhr.status
          //            +" Response: "+xhr.responseText)
          $(jquery_card_selector).html("Please report this error: "+errorThrown+xhr.status+xhr.responseText);
          $(jquery_card_selector).addClass("alert alert-danger");
        }
      });
}

/**
 * Submit an ajax call for updating an card in the surfaces view.
 *
 * @param card_url {String} URL to call in order to get card content as HTTP response
 * @param surface_id {Number} Id of the surface being displayed
 */
function submit_surface_card_ajax(card_url, surface_id) {

      var jquery_card_selector = "#card-"+surface_id;

      // console.log("Submitting AJAX call for surface card "+jquery_card_selector+"..");

      $.ajax({
        type: "GET",
        url: card_url,
        timeout: 0,
        data: {
           surface_id: surface_id,
        },
        success : function(data, textStatus, xhr) {
            // console.log("Received response for card '" + jquery_card_selector + "'. Status: " + xhr.status);
            $(jquery_card_selector).html(data); // insert resulting HTML code
            if (xhr.status == 202) {
                // Data is not ready, retrigger AJAX call
                setTimeout(function () {
                    submit_surface_card_ajax(card_url, surface_id);
                }, 1000);
            }
        },
        error: function(xhr, textStatus, errorThrown) {
          // console.log("Error receiving response for card '"+card_element_id+"'. Status: "+xhr.status
          //            +" Response: "+xhr.responseText)
          $(jquery_card_selector).html("Please report this error: "+errorThrown+xhr.status+xhr.responseText);
          $(jquery_card_selector).addClass("alert alert-danger");
        }
      });
}



/*
 * Setup document handlers.
 */
$(document).ready(function ($) {
    $('.clickable-table-row').click(function () {
        window.document.location = $(this).data("href");
    });
});
