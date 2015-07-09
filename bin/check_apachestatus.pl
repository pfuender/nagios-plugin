#!/usr/bin/env perl
# nagios: -epn

####################### check_apachestatus.pl #######################
# Version : 1.1
# Date : 27 Jul 2007
# Author  : De Bodt Lieven (Lieven.DeBodt at gmail.com)
# Licence : GPL - http://www.fsf.org/licenses/gpl.txt
#############################################################
#
# help : ./check_apachestatus.pl -h

# $Id: check_apachestatus.pl 2185 2008-07-28 15:11:42Z fbrehm $
# $URL: http://maria.technik.berlin.strato.de:8080/svn-bs/nagios/trunk/plugins/check_apachestatus.pl $

use strict;
use warnings;
use Getopt::Long;
use LWP::UserAgent;
use Time::HiRes qw(gettimeofday tv_interval);

# Nagios specific

use lib "/usr/lib/nagios/plugins";
use utils qw(%ERRORS $TIMEOUT &print_revision &support &usage );

# Globals

my $Version = '1.1';
my $Name    = $0;
$Name =~ s#.*/##;

my $o_host          = undef;    # hostname
my $o_help          = undef;    # want some help ?
my $o_port          = undef;    # port
my $o_version       = undef;    # print version
my $o_warn_level    = undef;    # Number of available slots that will cause a warning
my $o_crit_level    = undef;    # Number of available slots that will cause an error
my $o_w_warn_level  = undef;    # Number of waiting slots that will cause a warning
my $o_w_crit_level  = undef;    # Number of waiting slots that will cause an error
my $o_k_warn_level  = undef;    # Number of keepalive slots that will cause a warning
my $o_k_crit_level  = undef;    # Number of keepalive slots that will cause an error
my $o_timeout       = 15;       # Default 15s Timeout
my $o_protocol      = 'http';   # 'http' or 'https'
my $o_auth          = undef;    # auth

my $w_warn_pc = undef;          # Bool: the $o_w_warn_level value is a percentage or not
my $w_crit_pc = undef;          # Bool: the $o_w_crit_level value is a percentage or not
my $k_warn_pc = undef;          # Bool: the $o_k_warn_level value is a percentage or not
my $k_crit_pc = undef;          # Bool: the $o_k_crit_level value is a percentage or not

# functions

#-------------------------------------------------

sub show_versioninfo {
    print_revision($Name, $Version . ', $Revision: 2185 $' );
}

#-------------------------------------------------

sub print_usage {
    print "Usage: $Name -H <host> [-p <port>] [-P <protocol>] [-t <timeout>] [-w <warn_level> -c <crit_level>] [--w_warn <wconn_warn_level> --w_crit <wconn_crit_level>] [--k_warn <keepaliveconn_warn_level> --k_crit <keepaliveconnf_crit_level>]  [-V]\n";
}

#-------------------------------------------------

# Get the alarm signal
$SIG{'ALRM'} = sub {
    print("ERROR: Alarm signal (Nagios time-out)\n");
    exit $ERRORS{"CRITICAL"};
};

#-------------------------------------------------

sub help {
    show_versioninfo();
    print "Copyright (c) 2008 Strato AG, Frank Brehm

Apache Monitor for Nagios.
GPL licence, (c)2006-2007 De Bodt Lieven

";
    print_usage();

    print <<EOT;
-h, --help
   print this help message
-H, --hostname=HOST
   name or IP address of host to check
-p, --port=PORT
   Http port
-P, --protocol=PROTOCOL
   protocol to use ('http' or 'https')
-t, --timeout=INTEGER
   timeout in seconds (Default: $o_timeout)
-w, --warn=MIN
   number of available slots that will cause a warning
   -1 for no warning
-c, --critical=MIN
   number of available slots that will cause an error
--w_warn=INTEGER or PERCENTAGE
   number of waiting connections as total count or as a percentage
   of all slots that will cause a warning
--w_crit=INTEGER or PERCENTAGE
   number of waiting connections as total count or as a percentage
   of all slots that will cause an error
--k_warn=INTEGER or PERCENTAGE
   number of keepalive connections as total count or as a percentage
   of all slots that will cause a warning
--k_crit=INTEGER or PERCENTAGE
   number of keepalive connections as total count or as a percentage
   of all slots that will cause an error
-a, --auth=USER:PASS
   Set the authentication auth to user "USER" and password "PASS" if
   the server-status page is restricted.
-V, --version
   prints version number
Note :
  The script will return
    * Without warn and critical options:
        OK       if we are able to connect to the apache server's status page,
        CRITICAL if we aren't able to connect to the apache server's status page,,
    * With warn and critical options:
        OK       if we are able to connect to the apache server's status page and #available slots > <warn_level>,
        WARNING  if we are able to connect to the apache server's status page and #available slots <= <warn_level>,
        CRITICAL if we are able to connect to the apache server's status page and #available slots <= <crit_level>,
        UNKNOWN  if we aren't able to connect to the apache server's status page

Perfdata legend:
"_;S;R;W;K;D;C;L;G;I;."
_ : Waiting for Connection
S : Starting up
R : Reading Request
W : Sending Reply
K : Keepalive (read)
D : DNS Lookup
C : Closing connection
L : Logging
G : Gracefully finishing
I : Idle cleanup of worker
. : Open slot with no current process

EOT

    support();

} ## end sub help

#-------------------------------------------------

sub check_options {

    Getopt::Long::Configure("bundling");

    unless ( GetOptions(
        'help|h'          => \$o_help,
        'hostname|H=s'    => \$o_host,
        'port|p=i'        => \$o_port,
        'protocol|P=s'    => \$o_protocol,
        'version|V'       => \$o_version,
        'warn|w=i'        => \$o_warn_level,
        'critical|c=i'    => \$o_crit_level,
        'w_warn=s'        => \$o_w_warn_level,
        'w_crit=s'        => \$o_w_crit_level,
        'k_warn=s'        => \$o_k_warn_level,
        'k_crit=s'        => \$o_k_crit_level,
        'auth|a=s'        => \$o_auth,
        'timeout|t=i'     => \$o_timeout,
    ) ) {
        print_usage();
        exit $ERRORS{"UNKNOWN"};
    }

    if ( defined($o_help) ) {
        help();
        exit $ERRORS{"OK"};
    }

    if ( defined($o_version) ) {
        show_versioninfo();
        exit $ERRORS{"OK"}
    }

    if (   ( ( defined($o_warn_level) && !defined($o_crit_level) ) || ( !defined($o_warn_level) && defined($o_crit_level) ) )
        || ( ( defined($o_warn_level) && defined($o_crit_level) ) && ( ( $o_warn_level != -1 ) && ( $o_warn_level <= $o_crit_level ) ) ) )
    {
        warn "Check warn and crit!\n";
        print_usage();
        exit $ERRORS{"UNKNOWN"};
    }

    if ( (defined($o_w_warn_level) && !defined($o_w_crit_level)) ||
            (!defined($o_w_warn_level) && defined($o_w_crit_level)) ) {
            warn "Check warn and crit waiting connections!\n";
            print_usage();
            exit $ERRORS{"UNKNOWN"};
    }

    if ( defined($o_w_warn_level) ) {
        if ($o_w_warn_level =~ /^\s*(\d+)\s*(\%)?\s*$/) {
            $o_w_warn_level = int($1);
            if ( $2 ) {
                $w_warn_pc = 1;
            }
        }
        else {
            warn "Check warn waiting connections!\n";
            print_usage();
            exit $ERRORS{"UNKNOWN"};
        }
    }

    if ( defined($o_w_crit_level) ) {
        if ($o_w_crit_level =~ /^\s*(\d+)\s*(\%)?\s*$/) {
            $o_w_crit_level = int($1);
            if ( $2 ) {
                $w_crit_pc = 1;
            }
        }
        else {
            warn "Check crit waiting connections!\n";
            print_usage();
            exit $ERRORS{"UNKNOWN"};
        }
    }

    if ( defined($o_w_warn_level) &&  defined($o_w_crit_level) ) {
        if ( $o_w_crit_level < $o_w_warn_level ) {
            warn "Check warn and crit waiting connections!\n";
            print_usage();
            exit $ERRORS{"UNKNOWN"};
        }
    }

    if ( (defined($o_k_warn_level) && !defined($o_k_crit_level)) ||
            (!defined($o_k_warn_level) && defined($o_k_crit_level)) ) {
            warn "Check warn and crit keepalive connections!\n";
            print_usage();
            exit $ERRORS{"UNKNOWN"};
    }

    if ( defined($o_k_warn_level) ) {
        if ($o_k_warn_level =~ /^\s*(\d+)\s*(\%)?\s*$/) {
            $o_k_warn_level = int($1);
            if ( $2 ) {
                $k_warn_pc = 1;
            }
        }
        else {
            warn "Check warn keepalive connections!\n";
            print_usage();
            exit $ERRORS{"UNKNOWN"};
        }
    }

    if ( defined($o_k_crit_level) ) {
        if ($o_k_crit_level =~ /^\s*(\d+)\s*(\%)?\s*$/) {
            $o_k_crit_level = int($1);
            if ( $2 ) {
                $k_crit_pc = 1;
            }
        }
        else {
            warn "Check crit keepalive connections!\n";
            print_usage();
            exit $ERRORS{"UNKNOWN"};
        }
    }

    if ( defined($o_k_warn_level) &&  defined($o_k_crit_level) ) {
        if ( $o_k_crit_level < $o_k_warn_level ) {
            warn "Check warn and crit keepalive connections!\n";
            print_usage();
            exit $ERRORS{"UNKNOWN"};
        }
    }

    # Check compulsory attributes
    if ( !defined($o_host) ) {
        print_usage();
        exit $ERRORS{"UNKNOWN"};
    }

    $o_protocol = lc($o_protocol);
    unless ( $o_protocol eq 'http' or $o_protocol eq 'https' ) {
        warn "Use correct protocol!\n";
        print_usage();
        exit $ERRORS{"UNKNOWN"};
    }

} ## end sub check_options

########## MAIN ##########

check_options();

my $ua = LWP::UserAgent->new( protocols_allowed => ['http', 'https'], timeout => $o_timeout );

my $url = $o_protocol . '://' . $o_host;
$url .= ':' . $o_port if defined $o_port;
$url .= '/server-status?auto';

my $req = HTTP::Request->new(GET => $url);
$req->authorization_basic( split( /:/, $o_auth ) ) if $o_auth;

my $timing0  = [gettimeofday];
my $response = $ua->request($req);
my $timeelapsed = tv_interval( $timing0, [gettimeofday] );

my $webcontent = undef;

if ( $response->is_success ) {
    $webcontent = $response->content;
    my @webcontentarr = split( "\n", $webcontent );
    my $i             = 0;
    my $BusyWorkers   = undef;
    my $IdleWorkers   = undef;
    my $ScoreBoard = "";
    my $scoreboard_started = undef;
    my $ReqPerSec  = undef;

    for my $line ( @webcontentarr ) {

        if ( $line =~ /^\s*Busy(?:Workers|Servers):\s*(\d+)/i ) {
            $BusyWorkers = $1;
            next;
        }

        if ( $line =~ /^\s*Idle(?:Workers|Servers):\s*(\d+)/i ) {
            $IdleWorkers= $1;
            next;
        }

        if ( $line =~ /^\s*ReqPerSec:\s*([\.0-9]+)/i ) {
            $ReqPerSec = $1 + 0;
        }

        if ( $line =~ /^\s*Scoreboard:\s*([_SRWKDCLGI\.]+)/i ) {
            $ScoreBoard .= $1;
            $scoreboard_started = 1;
            next;
        }

        if ( $scoreboard_started ) {
            if ( $line =~ /^\s*([_SRWKDCLGI\.]+)/i ) {
                $ScoreBoard .= $1;
            }
            else {
                $scoreboard_started = undef;
            }
        }

    }

    # warn "Anzahl Slots: " . length($ScoreBoard) . "\n";
    my $reqpersec_out = defined $ReqPerSec ? sprintf( " ReqPerSec=%f;;;0", $ReqPerSec ) : '';

    # count open slots
    my $CountOpenSlots = ( $ScoreBoard =~ tr/\.// );
    my $CountAllSlots = length($ScoreBoard);
    my $CountWaitingConnections = ( $ScoreBoard =~ tr/W// );
    my $CountKeepaliveConnections = ( $ScoreBoard =~ tr/K// );

    my $w_crit_level = $o_w_crit_level;
    if ( defined($o_w_crit_level) and $w_crit_pc ) {
        $w_crit_level = $o_w_crit_level * $CountAllSlots / 100;
    }

    my $w_warn_level = $o_w_warn_level;
    if ( defined($o_w_warn_level) and $w_warn_pc ) {
        $w_warn_level = $o_w_warn_level * $CountAllSlots / 100;
    }

    my $k_crit_level = $o_k_crit_level;
    if ( defined($o_k_crit_level) and $k_crit_pc ) {
        $k_crit_level = $o_k_crit_level * $CountAllSlots / 100;
    }

    my $k_warn_level = $o_k_warn_level;
    if ( defined($o_k_warn_level) and $k_warn_pc ) {
        $k_warn_level = $o_k_warn_level * $CountAllSlots / 100;
    }

    my $label = 'OK';
    if ( ( defined($o_crit_level) && ( $o_crit_level != -1 ) ) and ( ( $CountOpenSlots + $IdleWorkers ) <= $o_crit_level )  ) {
        $label = 'CRITICAL';
    }
    elsif ( defined($w_crit_level) and ($CountWaitingConnections >= $w_crit_level) ) {
        $label = 'CRITICAL';
    }
    elsif ( defined($k_crit_level) and ($CountKeepaliveConnections >= $k_crit_level) ) {
        $label = 'CRITICAL';
    }
    elsif ( ( defined($o_warn_level) && ( $o_warn_level != -1 ) ) and ( ( $CountOpenSlots + $IdleWorkers ) <= $o_warn_level ) ) {
        $label = 'WARNING';
    }
    elsif ( defined($w_warn_level) and ($CountWaitingConnections >= $w_warn_level) ) {
        $label = 'WARNING';
    }
    elsif ( defined($k_warn_level) and ($CountKeepaliveConnections >= $k_warn_level) ) {
        $label = 'WARNING';
    }

    my $w_c = '';
    if ( defined($w_crit_level) ) {
        $w_c = sprintf('%d', $w_crit_level);
    }

    my $w_w = '';
    if ( defined($w_warn_level) ) {
        $w_w = sprintf('%d', $w_warn_level);
    }

    my $k_c = '';
    if ( defined($k_crit_level) ) {
        $k_c = sprintf('%d', $k_crit_level);
    }

    my $k_w = '';
    if ( defined($k_warn_level) ) {
        $k_w = sprintf('%d', $k_warn_level);
    }

    printf( "%s %f seconds response time. Idle %d, busy %d, waiting %d, keepalive %d, open slots %d | waiting=%d;%s;%s;0 keepalive=%d;%s;%s;0 busy=%d;;;0 idle=%d;;;0 open=%d;;;0 resp_time=%f;;;0",
        $label, $timeelapsed,
        $IdleWorkers, $BusyWorkers, $CountWaitingConnections, $CountKeepaliveConnections, $CountOpenSlots,
        $CountWaitingConnections, $w_w, $w_c,
        $CountKeepaliveConnections, $k_w, $k_c,
        $BusyWorkers,
        $IdleWorkers,
        $CountOpenSlots,
        $timeelapsed );
    print $reqpersec_out . "\n";

    exit $ERRORS{$label};

} ## end if ( $response->is_success )
else {

    if ( defined($o_warn_level) || defined($o_crit_level) ) {
        printf( "UNKNOWN %s\n", $response->status_line );
        exit $ERRORS{"UNKNOWN"};
    }
    else {
        printf( "CRITICAL %s\n", $response->status_line );
        exit $ERRORS{"CRITICAL"};
    }

} ## end else [ if ( $response->is_success )

# vim: ts=4 et
