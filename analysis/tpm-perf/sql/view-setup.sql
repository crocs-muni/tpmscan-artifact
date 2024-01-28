create materialized view view_algorithms
as select distinct measurement_id, algorithm_id from data;

create view view_firmware
as 	select	measurement.id as id,
		measurement.source as source,
		to_version(measurement.firmware) as firmware
	  from	measurement;
