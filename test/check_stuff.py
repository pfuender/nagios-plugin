#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010-2013 by Profitbricks GmbH
@license: GPL3
@summary: an example Nagios plugin using the nagios.plugin modules.
'''

import os
import sys
import logging
import textwrap
import random

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import ColoredFormatter, pp, init_root_logger

import nagios

from nagios.plugin import NagiosPluginError
from nagios.plugin import NagiosPlugin

from nagios.plugin.range import NagiosRange

log = logging.getLogger(__name__)

__version__ = '1.0'

#==============================================================================

if __name__ == '__main__':

    blurb = """\
    This plugin is an example of a Nagios plugin written in Python2 using the
    nagios.plugin modules and the NagiosPlugin class.
    It will generate a random integer between 1 and 20 (though you can specify
    the number with the -r option for testing), and will output nagios.state.ok,
    nagios.state.warning or nagios.state.critical if the resulting number is
    outside the specified thresholds.
    """

    blurb = textwrap.dedent(blurb).strip()

    extra = """\
    THRESHOLDs for -w and -c are specified 'min:max' or 'min:' or ':max'
    (or 'max'). If specified '@min:max', a warning status will be generated
    if the count *is* inside the specified range.

    See more threshold examples at:
        http://nagiosplug.sourceforge.net/developer-guidelines.html#THRESHOLDFORMAT

    Examples:

        %(prog)s -w 10 -c 18

            Returns a warning, if the resulting number is greater than 10,
            or a critical error, if it is greater than 18.

        %(prog)s -w 10: -c 4:

            Returns a warning, if the resulting number is less than 10,
            or a critical error, if it is less than 4.

    """

    progname = os.path.basename(sys.argv[0])
    extra = textwrap.dedent(extra).strip() % {'prog': progname}

    plugin = NagiosPlugin(
            usage = '''%(prog)s [ -v|--verbose ] [-t <timeout>]
    -c|--critical <critical threshold>
    -w|--warning <warning threshold>
    [-r|--result <INTEGER>]''',
            version = __version__,
            url = 'http://www.profitbricks.com',
            blurb = blurb,
            extra = extra,
    )

    help_warn = """\
    Minimum and maximum number of allowable result, outside of which a
    warning will be generated. If omitted, no warning is generated.
    """
    help_warn = textwrap.dedent(help_warn)

    help_crit = """\
    Minimum and maximum number of allowable result, outside of which a
    critical will be generated.
    """
    help_crit = textwrap.dedent(help_crit)

    help_result = """\
    Specify the result on the command line rather than generating a
    random number. For testing.
    """
    help_result = textwrap.dedent(help_result)

    plugin.add_arg(
            '-w', '--warning',
            type = NagiosRange,
            metavar = 'RANGE',
            dest = 'warning',
            required = True,
            help = help_warn,
    )

    plugin.add_arg(
            '-c', '--critical',
            type = NagiosRange,
            metavar = 'RANGE',
            dest = 'critical',
            required = True,
            help = help_crit,
    )

    plugin.add_arg(
            '-r', '--result',
            type = int,
            metavar = 'INTEGER',
            dest = 'result',
            help = help_result,
    )

    plugin.parse_args()
    verbose = plugin.argparser.args.verbose
    init_root_logger(verbose)

    plugin.set_thresholds(
        warning = plugin.argparser.args.warning,
        critical = plugin.argparser.args.critical,
    )

    result = plugin.argparser.args.result
    if result is None:
        result = random.randint(1, 20)
        log.debug("Checking result value of %d.", result)
    else:
        if result < 0 or result > 20:
            plugin.die((" invalid number supplied for the -r option, " +
                    "must be between 0 and 20"))

    plugin.add_perfdata(
            label = 'Result',
            value = result,
            threshold = plugin.threshold,
            min_data = 0,
            max_data = 20,
    )

    if verbose > 1:
        log.debug("Plugin object:\n" + pp(plugin.as_dict()))

    plugin.exit(
            code = plugin.check_threshold(result),
            message = (" sample result was %d" % (result))
    )

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
