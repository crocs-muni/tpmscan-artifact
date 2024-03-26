explain	select percentile_cont(0.5) within group (order by data.value) as median,
       	measurement.stamp as stamp

   from	device
   join	measurement
     on	device.id = measurement.device_id

   join	data
     on	data.measurement_id = measurement.id

   join	algorithm
     on	algorithm.id = data.algorithm_id

  where	device.hostname like 'musa%'
    and	algorithm.name = 'Perf_HMAC'
    and	measurement.stamp between '2022-12-01' and '2022-12-20'
    and	date(measurement.stamp) != '2022-12-08'

group by	measurement.stamp
order by	median desc;
