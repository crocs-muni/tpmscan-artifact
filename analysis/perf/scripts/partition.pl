#!/usr/bin/env perl

use v5.36;
use utf8;

use open ':std', ':encoding(utf-8)';

use Data::Printer;
use DBD::Pg;
use DBI;
use Env qw{$TPM_DB_NAME};

my $db_name = $TPM_DB_NAME // 'tpm';
my $db = DBI->connect("dbi:Pg:dbname=$db_name", '', '', {AutoCommit => 0});

sub devices($db) {
	return $db->selectcol_arrayref(qq{
		  select  distinct id
		    from  device
		order by  id
	}, {})->@*;
}

sub create_partitions($db, $default) {
	say "□ Discovering data";

	say "  • Devices";
	my @devices = devices($db);

	say "□ Creating indices";
	foreach my $column (qw{measurement algorithm}) {
		$db->do(qq{
			create index if not exists ix_data_${column}_id
			on data (${column}_id);
		}, {});
	}

	say "□ Creating partitions";
	foreach my $device_id (@devices) {
		printf "  • %8d ", $device_id;

		$db->do(qq{
			create table if not exists data_${device_id}
			partition of data
			for values in (?)
		}, {}, $device_id);

		say "✓ ";
		$db->commit;
	}
}

create_partitions($db, 'data_default');
