with constraints as (
	select 	a.name as algorithm,
		c.vendor as vendor,
		c.firmware as firmware,
		c.firmware_string as firmware_string
	  from	algorithm as a, view_chips as c
	 where	(c.vendor = 'IFX' and c.firmware_string = '5.63.13.6400')
    	    or	(c.vendor = 'NTC' and c.firmware_string = '7.2.2.0')
)
select 	c.algorithm as algorithm,
	c.vendor as vendor,
	c.firmware_string as firmware,
	(	select 	percentile_cont(0.5) within group (order by data.value)
		  from	data
		  join  device on device.id = data.device_id
		  join	measurement on measurement.id = data.measurement_id
		  join	algorithm on data.algorithm_id = algorithm.id
		 where	((device.id = 1)
			or	(device.id = 2 and date(measurement.stamp) != '2022-12-18'))
		   and	measurement.vendor = c.vendor
		   and	measurement.firmware = c.firmware
		   and	measurement.stamp < '2023-06-30'
		   and  algorithm.name = c.algorithm
	) / nullif((	select 	percentile_cont(0.5) within group (order by data.value)
		  from	data
		  join  device on device.id = data.device_id
		  join	measurement on measurement.id = data.measurement_id
		  join	algorithm on algorithm.id = data.algorithm_id
		 where	device.hostname not like 'nymfe%' and device.hostname not like 'musa%'
		   and	measurement.vendor = c.vendor
		   and	measurement.firmware = c.firmware
		   and	measurement.stamp < '2023-06-30'
		   and  algorithm.name = c.algorithm
	), 0) as factor
  from	constraints as c

order by	c.vendor desc, c.algorithm desc;
