#!/usr/bin/env perl

use v5.36;
use utf8;

use Data::Printer;
use DBD::Pg;
use DBI;

sub fix_occurrences($db, $row) {
	my $ids = $db->selectcol_arrayref(qq{
		select id
		  from device
		 where hostname = ?
		 order by id asc
	}, {}, $row->{hostname});

	my ($primary, @copies) = $ids->@*;

	say "  Keeping $primary";

	foreach my $copy (@copies) {
		say "  $copy -> $primary";
		my $changed = $db->do(qq{
			update measurement
			   set device_id = ?
			 where device_id = ?
		}, {}, $primary, $copy);

		say "  $copy -> $primary changed $changed";

		say "  Removing $copy";
		$db->do(qq{
			delete from device
			      where device.id = ?
		}, {}, $copy);
	}
}

sub scan_devices($db) {
	my $rows = $db->selectall_arrayref(qq{
		select count(*) as count,
		       hostname

		  from device

		 group by hostname
		 order by hostname
	}, {Slice => {}});

	foreach my $row ($rows->@*) {
		if ($row->{count} <= 1) {
			say "$row->{hostname} is OK, skipping";
			next;
		}

		say "$row->{hostname} has $row->{count} occurrences, fixing";
		fix_occurrences($db, $row);
	}
}

my $db = DBI->connect("dbi:Pg:dbname=tpm", '', '', {AutoCommit => 0});

scan_devices($db);

$db->commit;
