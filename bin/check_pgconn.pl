#!/usr/bin/perl -W
use strict;
use DBI;
use Getopt::Long;
use vars qw($opt_h $opt_w $opt_c $opt_H $opt_C $opt_d $opt_u $opt_p $PROGNAME);
use lib "/usr/lib/nagios/plugins" ;
use utils qw(%ERRORS &print_revision &usage);

$PROGNAME = "check_pgconn.pl";
my $USAGE    = "Usage: $PROGNAME -H <host> -d <database> -u <username> -p <password> -w <warn> -c <crit>\n";

Getopt::Long::Configure('bundling');
GetOptions
        ("h"   => \$opt_h, "help"       => \$opt_h,
         "w=s" => \$opt_w, "warning=s"  => \$opt_w,
         "c=s" => \$opt_c, "critical=s" => \$opt_c,
         "H=s" => \$opt_H, "hostname=s" => \$opt_H,
         "d=s" => \$opt_d, "database=s" => \$opt_d,
         "u=s" => \$opt_u, "username=s" => \$opt_u,
         "p=s" => \$opt_p, "password=s" => \$opt_p,
);

if ($opt_h) {&print_help(); exit $ERRORS{'OK'};}

length($opt_H) || &print_usage();
my $host = $1 if ($opt_H =~ /^([-.A-Za-z0-9]+)$/);
length($host) || usage("Invalid host: $opt_H\n");

length($opt_d) || &print_usage();
my $dbname = $1 if ($opt_d =~ /^([-A-Za-z0-9_]+)$/);
length($dbname) || usage("Invalid database name: $opt_d\n");

length($opt_u) || &print_usage();
my $username = $1 if ($opt_u =~ /^([-A-Za-z0-9_]+)$/);
length($username) || usage("Invalid username: $opt_u\n");

length($opt_p) || &print_usage();
my $password = $opt_p;
$password = "" if ($password =~ /\s/);
length($password) || usage("password may not contain whitespaces\n");

length($opt_w) || &print_usage();
my $warning = $1 if ($opt_w =~ /^([0-9]{1,2}|100)+$/);
length($warning) || usage("Invalid warning threshold: $opt_w\n");

length($opt_c) || &print_usage();
my $critical = $1 if ($opt_c =~ /^([0-9]{1,2}|100)$/);
length($critical) || usage("Invalid critical threshold: $opt_c\n");



my $status=$ERRORS{'UNKNOWN'};

#Connect to Database
my $Con = "DBI:Pg:dbname=$dbname;host=$host";
my $Dbh = DBI->connect($Con, $username, $password) || &error("Unable to access Database $dbname on host $host as user $username. Error returned was: ". $DBI::errstr);

my $sql = "SHOW max_connections;";

my $sth = $Dbh->prepare($sql) or &error("cannot prepare sql statement: '$sql': ".$Dbh->errstr);
$sth->execute() or &error("cannot execute sql statement: '$sql': ".$Dbh->errstr);
my $max_conn = -1;
while ( my ($mconn) = $sth->fetchrow() ) {
    $max_conn=$mconn;
}
$sth->finish();

$sql = "SELECT COUNT(*) FROM pg_stat_activity;";
$sth = $Dbh->prepare($sql) or &error("cannot prepare sql statement: '$sql': ".$Dbh->errstr);
$sth->execute() or &error("cannot execute sql statement: '$sql': ".$Dbh->errstr);
my $curr_conn = -1;
while ( my ($conn) = $sth->fetchrow() ) {
    $curr_conn=$conn;
}
$sth->finish();
$Dbh->disconnect();

my $avail_conn=$max_conn-$curr_conn;
my $avail_pct=$avail_conn/$max_conn*100;
my $used_pct=sprintf("%2.1f", $curr_conn/$max_conn*100);

#print "Max: $max_conn, Curr $curr_conn, Avail:$avail_conn, Avail Pct:$avail_pct, Used Pct: $used_pct, W: $warning, C: $critical\n";

my $code = "UNKNOWN";
if ($used_pct > $critical) {
    $code = "CRITICAL";
} elsif ($used_pct > $warning) {
    $code = "WARNING";
} else {
    $code = "OK";
}
my $msg="$code: $curr_conn of $max_conn Connections Used ($used_pct%)\n";

print $msg;
$status=$ERRORS{$code};
exit $status;

########################################

sub error {
    my $err = shift;
    print STDERR "$err\n";
    exit $ERRORS{'CRITICAL'};
}

sub print_usage () {
        usage $USAGE;
}

sub print_help () {
        print "$USAGE
-H, --hostname=HOST
   Name or IP address of host to check
-d, --database=DBNAME
   database name to connect to
-u, --username=DBNAME
   database username
-p, --password=PW
-w, --warning=INTEGER
   Percentage of used connections resulting in WARNING state
-c, --critical=INTEGER
   Percentage of used connections resulting in CRITICAL state

";
}
