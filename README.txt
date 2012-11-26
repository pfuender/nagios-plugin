======================================================
Base module for Nagios check plugins written in Python
======================================================

This package provides a family of Python modules
to streamline writing Nagios plugins.

These modules are rewritten modules originated by the
Perl module family Nagios::Plugin.

Following modules are supported:

 - nagios
   - classes:
     - state
       - readonly properties:
         - ok
         - warning
         - critical
         - unknown
         - dependent
 - nagios.plugin
   - constants:
     - OK
     - WARNING
     - CRITICAL
     - UNKNOWN
     - DEPENDENT
   - classes:
     - NagiosPlugin
     - NagiosPluginError
 - nagios.plugin.config
   - classes:
     - NagiosPluginConfig
 - nagios.plugin.functions
   - functions:
     - nagios_exit()
     - nagios_die()
     - check_messages()
     - get_shortname()
     - max_state()
     - max_state_alt()
 - nagios.plugin.getopt
     - classes:
       - NagiosPluginGetoptParser
 - nagion.plugin.perf
     - classes:
       - NagiosPluginPerformance
 - nagion.plugin.range
     - classes:
       - NagiosPluginRange
 - nagios.plugin.threshold
     - classes:
       - NagiosPluginThreshold


Author: Frank Brehm (<frank.brehm@profitbricks.com>)
