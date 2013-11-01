#!/usr/bin/perl
# nagios: -epn

use warnings;
use strict;

use Readonly;
use Data::Dumper;
use File::Basename;

BEGIN {
	if ( -d "/usr/local/nagios/perl/lib" ) {
		unshift(@INC, "/usr/local/nagios/perl/lib");
	}
	if ( -d "/opt/profitbricks/lib/perl" ) {
		unshift(@INC, "/opt/profitbricks/lib/perl");
	}
	if ( -d "/opt/nagios/lib/perl" ) {
		unshift(@INC, "/opt/nagios/lib/perl");
	}
	if ( -d "/opt/icinga/lib/perl" ) {
		unshift(@INC, "/opt/icinga/lib/perl");
	}
}

$Data::Dumper::Indent = 1;
$Data::Dumper::Sortkeys = 1;

$ENV{'PATH'}     = '/root/bin:/bin:/sbin:/usr/local/sbin:/usr/sbin:/usr/local/bin:/usr/bin:/usr/sfw/bin';
$ENV{'BASH_ENV'} = '';
$ENV{'ENV'}      = '';

#use lib "/usr/local/nagios/perl/lib" if -d "/usr/local/nagios/perl/lib";
#use lib "/opt/profitbricks/lib/perl" if -d "/opt/profitbricks/lib/perl";
#use lib "/opt/icinga/lib/perl" if -d "/opt/icinga/lib/perl";

use Nagios::Plugin;
use Nagios::Plugin::Threshold

$| = 1;

delete $ENV{'LC_ALL'} if exists $ENV{'LC_ALL'};
$ENV{'LC_CTYPE'} = 'POSIX';
$ENV{'LC_NUMERIC'} = 'POSIX';
$ENV{'LC_TIME'} = 'POSIX';
$ENV{'LC_COLLATE'} = 'POSIX';
$ENV{'LC_MONETARY'} = 'POSIX';
$ENV{'LC_MESSAGES'} = 'POSIX';

our ( $VERSION, $PROGNAME );

$VERSION = '0.3.1';

# get the base name of this script for use in the examples
$PROGNAME = basename($0);

my %Valid_Metric = (
    'PROCS'   => 1,
    'VSZ'     => 1,
    'RSS'     => 1,
    'CPU'     => 1,
    'ELAPSED' => 1,
);

my %C = ( 'min' => undef, 'max' => undef );
my %W = ( 'min' => undef, 'max' => undef );

my $usage = <<ENDE;
Usage: %s [-v|--verbose] [-t|--timeout=<timeout>] [-c|--critical=<critical threshold>] [-w|--warning=<warning threshold>]
    [-m|--metric=<metric>] [-s|--state=<statusflags>] [--ps-cmd=<command>]
    [-p|--ppid=<parent_pid>] [-r|--rss=<value>] [-P|--pcpu=<value>] [-z|--vsz=<value>] [-u|--user=<user_id>]
    [-a|--argument-array=<args>] [-C|--command=<command>] [-i|--init]
ENDE
$usage =~ s/(\[-p\|--ppid=)/[-Z|--zone=<zone>] $1/ if $^O eq 'solaris';
$usage =~ s/\s*$//;

my $blurb = <<ENDE;
Copyright (c) 2012 ProfitBricks GmbH, Berlin, Frank Brehm

Checks all processes and generates WARNING or CRITICAL states if the specified
metric is outside the required threshold ranges. The metric defaults to number
of processes.  Search filters can be applied to limit the processes to check.
ENDE

my $args = {};

my $p = Nagios::Plugin->new(
    'shortname' => 'PROCS',
    'usage'     => $usage,
    'version'   => $VERSION,
    'blurb'     => $blurb,
    'timeout'   => 15,
);

$p->add_arg(
    'spec'  => 'warning|w=s',
    'help'  => 'Generate warning state if metric is outside this range',
    'required' => 1,
);

$p->add_arg(
    'spec'  => 'critical|c=s',
    'help'  => 'Generate critical state if metric is outside this range',
    'required' => 1,
);

$p->add_arg(
    'spec'     => 'metric|m=s',
    'help'     => "Check thresholds against metric.\n   Valid values are: " . join( ', ', sort keys %Valid_Metric ) . "\n   Default: %s.",
    'required' => 1,
    'default'  => 'PROCS',
);

$args = {};
$args->{'spec'} = 'ps-cmd=s';
$args->{'help'} = "The ps-command (default: '%s')";
$args->{'required'} = 1;
$args->{'default'} = '/usr/bin/ps';

for my $d ( split( ":", $ENV{'PATH'} ) ) {
    my $ps_cmd = $d . "/ps";
    #warn "Checke '$ps_cmd' ...\n";
    if ( -x $ps_cmd ) {
        $args->{'default'} = $ps_cmd;
        last;
    }
}

$p->add_arg( %$args );

if ( $^O eq 'solaris' ) {
    $p->add_arg(
        'spec'     => 'zone|Z=s',
        'help'     => 'Name of the solaris zone to search for processes',
    );
}

$p->add_arg(
    'spec'     => 'state|s=s',
    'help'     => 'Only scan for processes that have, in the output of `ps`, one or
   more of the status flags you specify (for example R, Z, S, RS,
   RSZDT, plus others based on the output of your \'ps\' command).',
);

$p->add_arg(
    'spec'     => 'ppid|p=i',
    'help'     => 'Only scan for children of the parent process ID indicated.',
);

$p->add_arg(
    'spec'     => 'vsz|z=i',
    'help'     => 'Only scan for processes with vsz higher than indicated.',
);

$p->add_arg(
    'spec'     => 'rss|r=i',
    'help'     => 'Only scan for processes with rss higher than indicated.',
);

$p->add_arg(
    'spec'     => 'pcpu|P=i',
    'help'     => 'Only scan for processes with pcpu higher than indicated.',
);

$p->add_arg(
    'spec'     => 'user|u=s',
    'help'     => 'Only scan for processes with user name or ID indicated.',
);

$p->add_arg(
    'spec'     => 'args|argument-array|a=s',
    'help'     => 'Only scan for processes with args that contain STRING.',
);

$p->add_arg(
    'spec'     => 'command|C=s',
    'help'     => 'Only scan for exact matches of STRING (without path).',
);

$p->add_arg(
    'spec'     => 'init|i',
    'help'     => 'Only scan for processes, they are direct childs of init.',
);

# Parse arguments and process standard ones (e.g. usage, help, version)
$p->getopts;

our $verbose = $p->opts->verbose;

##############################
# perform sanity checking on command line options

# critical-Parameter
if ( $p->opts->critical =~ /^\s*(\d+)\s*$/ ) {
    $C{'min'} = $1;
}
elsif ( $p->opts->critical =~ /^\s*(\d+)\s*:\s*$/ ) {
    $C{'min'} = $1;
}
elsif ( $p->opts->critical =~ /^\s*(\d+)\s*:\s*(\d+)\s*$/ ) {
    $C{'min'} = $1;
    $C{'max'} = $2;
}
elsif ( $p->opts->critical =~ /^\s*:\s*(\d+)\s*$/ ) {
    $C{'max'} = $1;
}
else {
    $p->nagios_die( sprintf( "Invalid critical value '%s'.", $p->opts->critical ) );
}

# warning-Parameter
if ( $p->opts->warning =~ /^\s*(\d+)\s*$/ ) {
    $W{'min'} = $1;
}
elsif ( $p->opts->warning =~ /^\s*(\d+)\s*:\s*$/ ) {
    $W{'min'} = $1;
}
elsif ( $p->opts->warning =~ /^\s*(\d+)\s*:\s*(\d+)\s*$/ ) {
    $W{'min'} = $1;
    $W{'max'} = $2;
}
elsif ( $p->opts->warning =~ /^\s*:\s*(\d+)\s*$/ ) {
    $W{'max'} = $1;
}
else {
    $p->nagios_die( sprintf( "Invalid warning value '%s'.", $p->opts->warning ) );
}

# UID oder Nutzername
my $user = undef;
if ( defined $p->opts->user ) {
    if ( $p->opts->user =~ /^\s*(\d+)\s*$/ ) {
        my $uid = $1;
        $user = getpwuid($uid);
        unless ( $user ) {
            $user = $uid;
            warn sprintf( "UID '%s' was not found.\n", $p->opts->user ) if $verbose;
        }
        #$p->nagios_die( sprintf( "UID %s was not found", $p->opts->user ) ) unless $user;
    }
    else {
        my $uid = getpwnam($p->opts->user);
        $p->nagios_die( sprintf( "User name %s was not found", $p->opts->user ) ) unless defined $uid;
        $user = $p->opts->user;
    }
}

if ( $p->opts->metric ) {
    $p->nagios_die( sprintf( "Invalid metric '%s'.", $p->opts->metric ) ) unless $Valid_Metric{$p->opts->metric};
}

if ( $verbose >= 2 ) {
    warn "Used filters:\n";
    warn sprintf "  Critical:   min %s max %s\n", ( defined $C{'min'} ? $C{'min'} : '(undef)' ), ( defined $C{'max'} ? $C{'max'} : '(undef)' );
    warn sprintf "  Warning:    min %s max %s\n", ( defined $W{'min'} ? $W{'min'} : '(undef)' ), ( defined $W{'max'} ? $W{'max'} : '(undef)' );
    warn "  PPID:       " . $p->opts->ppid . "\n" if defined $p->opts->ppid;
    warn "  User:       '" . $user . "'\n" if defined $user;
    warn "  Status:     '" . $p->opts->state . "'\n" if $p->opts->state;
    warn "  Command:    '" . $p->opts->command . "'\n" if $p->opts->command;
    warn "  Arguments:  '" . $p->opts->args . "'\n" if $p->opts->args;
    warn "  RSS:        " . $p->opts->rss . "\n" if defined $p->opts->rss;
    warn "  VSZ:        " . $p->opts->vsz . "\n" if defined $p->opts->vsz;
    warn "  PCPU:       " . $p->opts->pcpu . "\n" if defined $p->opts->pcpu;
    warn "  Zone:       '" . $p->opts->zone . "'\n" if defined $^O eq 'solaris' and $p->opts->zone;
    warn "  Metric:     " . $p->opts->metric . "\n";
    warn "  Init child: yes\n" if $p->opts->init;
    warn "ps command:     " . $p->opts->get('ps-cmd') . "\n";
    warn "timeout:        " . $p->opts->timeout . " seconds\n";
    warn "\n";
}

collect_processes();

$p->nagios_exit( OK, "All nice and cute" );

#------------------------------------------------------------------

sub collect_processes {

    my $zone = $^O eq 'solaris' ? $p->opts->zone : undef;
    my $bin_ps_cmd = $p->opts->get('ps-cmd');
    my $timeout = $p->opts->timeout;

    my $init_pid = {};
    my $found_procs = [];
    my $filterd_procs = [];

    my @Lines = ();
    my @fields = qw( user pid ppid s pcpu vsz rss time comm args );
    unshift @fields, "zone" if $zone;
    my $cmd = $bin_ps_cmd . " -e -o " . join( ",", @fields );
    warn sprintf "performing command '%s' ...\n", $cmd if $verbose;

    #return;

    eval {
        local $SIG{ALRM} = sub { die "timeout\n" };
        alarm $timeout;
        @Lines = `$cmd`;
        alarm 0;
        if ( $? ) {
            die "Abnormal result state " . $? . " of '" . $cmd . "'\n";
        }
    };
    warn "\n" if $verbose;
    if ($@) {
        $p->nagios_die( "Terminated because of: " . $@ );
    }

    # '              bsagent   9154      18762     Z         -                      0         0         00:00                              <defunct> <defunct>'
    #                user      pid       ppid      s         pcpu                   vsz       rss       time                               cmd       args
    my $match = '\\s*(\\S+)\\s+(\\d+)\\s+(\\d+)\\s+(\\S+)\\s+(-|\\d+(?:\\.\\d*))\\s+(\\d+)\\s+(\\d+)\\s+((?:(?:\\d+-)?\\d+:)?\\d+:\\d+)(?:\\s+(\\S+))\\s+(.*)';
    $match = '\\s*(\\S+)' . $match if $zone;
    warn sprintf( "Matching string: '" . $match . "'\n" ) if $verbose >= 2;

    shift @Lines;

    for my $line ( @Lines ) {

        warn $line if $verbose > 3;
        chomp $line;

        my @psfields;
        my $ps_info = {};

        unless ( @psfields = $line =~/^$match$/ ) {
            warn "Could not parse line: '$line'\n";
            next;
        }

        $ps_info->{'zone'}  = shift @psfields if $zone;
        $ps_info->{'user'}  = shift @psfields;
        $ps_info->{'pid'}   = shift @psfields;
        $ps_info->{'ppid'}  = shift @psfields;
        $ps_info->{'s'}     = shift @psfields;
        $ps_info->{'pcpu'}  = shift @psfields;
        $ps_info->{'vsz'}   = shift @psfields;
        $ps_info->{'rss'}   = shift @psfields;
        $ps_info->{'time'}  = shift @psfields;
        $ps_info->{'cmd'}   = shift @psfields;
        $ps_info->{'args'}  = shift @psfields;

        $ps_info->{'pcpu'} = 0 if $ps_info->{'pcpu'} and $ps_info->{'pcpu'} eq "-";
        $ps_info->{'pcpu'} += 0 if defined $ps_info->{'pcpu'};
        $ps_info->{'rss'} += 0 if defined $ps_info->{'rss'};
        $ps_info->{'vsz'} += 0 if defined $ps_info->{'vsz'};

        $ps_info->{'secs'}  = convert_to_seconds( $ps_info->{'time'} );
        $ps_info->{'cmd'}   = '' unless defined $ps_info->{'cmd'};
        $ps_info->{'args'}  = $ps_info->{'cmd'} unless defined $ps_info->{'args'};

        if ( $verbose >= 3 ) {
            my $out = sprintf( "user=%s pid=%d ppid=%d s=%s pcpu=%s vsz=%d rss=%d time=%s secs cmd='%s' args='%s'\n",
                               $ps_info->{'user'}, $ps_info->{'pid'}, $ps_info->{'ppid'}, $ps_info->{'s'}, $ps_info->{'pcpu'},
                               $ps_info->{'vsz'}, $ps_info->{'rss'}, ( defined $ps_info->{'secs'} ? $ps_info->{'secs'} : '(unknown)' ),
                               $ps_info->{'cmd'}, $ps_info->{'args'} );
            $out = "zone=" . $ps_info->{'zone'} . " " . $out if $zone;
            warn $out;

        }

        # Ignore self
        next if $ps_info->{'pid'} == $$;

        if ( $^O eq 'solaris' ) {
            $init_pid->{ $ps_info->{'pid'} } = 1 if ( $ps_info->{'cmd'} eq '/sbin/init' and $ps_info->{'pid'} == 1 )
                                                    or ( $ps_info->{'cmd'} eq 'zsched' and ( $ps_info->{'ppid'} == 1 or $ps_info->{'pid'} == $ps_info->{'ppid'} ) );
        }
        elsif ( $^O eq 'linux' ) {
            $init_pid->{ $ps_info->{'pid'} } = 1 if $ps_info->{'cmd'} =~ /init/ and $ps_info->{'ppid'} == 0;
        }

        push @$found_procs, $ps_info;

    }

    # Filterung der Prozess-Liste

    for my $ps_info ( @$found_procs ) {

        my $found = 1;
#        $found = 0 if $zone or $p->opts->state or $p->opts->ppid or defined $user or $p->opts->command or $p->opts->args or
#                      defined $p->opts->rss or defined $p->opts->vsz or defined $p->opts->pcpu or $p->opts->init;

        if ( $zone ) {
            $found = 0 unless $ps_info->{'zone'} eq $zone;
        }

        if ( $p->opts->init ) {
            $found = 0 unless $init_pid->{ $ps_info->{'ppid'} };
        }

        if ( $p->opts->state ) {
            my $state = $ps_info->{'s'};
            my $s = join( '|', split( //, uc($p->opts->state) ) );
            my $cnt = $state =~ /$s/;
            $found = 0 unless $cnt;
        }

        if ( defined $p->opts->ppid ) {
            $found = 0 unless $ps_info->{'ppid'} == $p->opts->ppid;
        }

        if ( defined $user ) {
            $found = 0 unless $user eq $ps_info->{'user'};
        }

        if ( $p->opts->command ) {
            $found = 0 unless $p->opts->command eq $ps_info->{'cmd'};
        }

        if ( $p->opts->args ) {
            my $c = $p->opts->args;
            $found = 0 unless $ps_info->{'args'} =~ /$c/;
        }

        if ( defined $p->opts->rss ) {
            $found = 0 unless defined $ps_info->{'rss'} and $ps_info->{'rss'} >= $p->opts->rss;
        }

        if ( defined $p->opts->vsz ) {
            $found = 0 unless defined $ps_info->{'vsz'} and $ps_info->{'vsz'} >= $p->opts->vsz;
        }

        if ( defined $p->opts->pcpu ) {
            $found = 0 unless defined $ps_info->{'pcpu'} and $ps_info->{'pcpu'} >= $p->opts->pcpu;
        }

        push @$filterd_procs, $ps_info if $found;

    }

    $found_procs = undef;

    if ( $verbose >= 2 ) {
        warn "Gefundene Init-PID's: " . Dumper($init_pid);
        warn "Gefundene Prozesse: " . Dumper($filterd_procs);
    }

    my @FilterDescs;
    push @FilterDescs, sprintf( "zone '%s'", $zone ) if $zone;
    push @FilterDescs, "init child" if $p->opts->init;
    push @FilterDescs, sprintf( "state '%s'", $p->opts->state ) if $p->opts->state;
    push @FilterDescs, sprintf( "PPID %s", $p->opts->ppid ) if defined $p->opts->ppid;
    push @FilterDescs, sprintf( "user '%s'", $user ) if defined $user;
    push @FilterDescs, sprintf( "command '%s'", $p->opts->command ) if $p->opts->command;
    push @FilterDescs, sprintf( "args '%s'", $p->opts->args ) if $p->opts->args;
    push @FilterDescs, sprintf( "rss %s", $p->opts->rss ) if defined $p->opts->rss;
    push @FilterDescs, sprintf( "vsz %s", $p->opts->vsz ) if defined $p->opts->vsz;
    push @FilterDescs, sprintf( "pcpu %s", $p->opts->pcpu ) if defined $p->opts->pcpu;

    my $count = scalar(@$filterd_procs);
    my $value_total = 0;
    my $uom = '';
    my $perf_value = 'procs';
    for my $ps_info ( @$filterd_procs ) {
        my $value = 1;
        if ( $p->opts->metric eq 'VSZ' ) {
            $value = $ps_info->{'vsz'} || 0;
            $perf_value = 'vsz';
        }
        elsif ( $p->opts->metric eq 'RSS' ) {
            $value = $ps_info->{'rss'} || 0;
            $perf_value = 'rss';
        }
        elsif ( $p->opts->metric eq 'CPU' ) {
            $value = $ps_info->{'pcpu'} || 0;
            $uom = '%';
            $perf_value = 'cpu';
        }
        elsif ( $p->opts->metric eq 'ELAPSED' ) {
            $value = $ps_info->{'secs'} || 0;
            $uom = 'sec';
            $perf_value = 'elapsed_time';
        }
        $value_total += $value;
    }

    warn sprintf "Ermittelte Gesamt-Metrik (%s): %s%s\n", $p->opts->metric, $value_total, $uom if $verbose;

    my $status = OK;

    my $out = sprintf( "%d process%s", $count, ( $count == 1 ? '' : "es" ) );
    $out .= " with " . join( ", ", @FilterDescs ) if @FilterDescs;
    $out .= sprintf( ", %s=%s%s", $perf_value, $value_total, $uom ) if $p->opts->metric ne 'PROCS';

    my $warn = defined $W{'max'} ? $W{'max'} : $W{'min'};
    my $crit = defined $C{'max'} ? $C{'max'} : $C{'min'};

    my $t = Nagios::Plugin::Threshold->set_thresholds(
        'warning'  => $warn,
        'critical' => $crit,
    );

    $p->add_perfdata( label => $perf_value, value => $value_total, uom => $uom, threshold => $t );

    if ( defined $C{'max'} and $value_total > $C{'max'} ) {
        $status = CRITICAL;
    }
    elsif ( defined $C{'min'} and $value_total < $C{'min'} ) {
        $status = CRITICAL;
    }
    elsif ( defined $W{'max'} and $value_total > $W{'max'} ) {
        $status = WARNING;
    }
    elsif ( defined $W{'min'} and $value_total < $W{'min'} ) {
        $status = WARNING;
    }

    $p->nagios_exit( $status, $out );

}

#------------------------------------------------------------------

sub convert_to_seconds {

    my $etime = shift;

    my ( $days, $hours, $minutes, $seconds );
    my $result = 0;

    unless ( ( $days, $hours, $minutes, $seconds ) = $etime =~ /^\s*(?:(?:(\d+)-)?(\d+):)?(\d+):(\d+)/ ) {
        return undef;
    }

    $days = 0 unless defined $days;
    $hours = 0 unless defined $hours;
    $result = ( $days * 86400 ) + ( $hours * 3600 ) + ( $minutes * 60 ) + $seconds;

    return $result;

}

#------------------------------------------------------------------


