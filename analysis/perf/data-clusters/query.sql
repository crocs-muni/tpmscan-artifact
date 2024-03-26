      select	device.hostname as hostname,
            	measurement.stamp, measurement.id,
            	round(percentile_cont(0.5) within group (order by data.value)::numeric, 5) as median,
            	round(stddev(data.value)::numeric, 5) as stddev

    from	data
        join	device on data.device_id = device.id
        join	measurement on data.measurement_id = measurement.id
        join	algorithm on data.algorithm_id = algorithm.id

   where	device.hostname like 'musa%'
     and	algorithm.name = 'Perf_GetRandom'
     and	date(measurement.stamp) = '2022-12-08'

group by	device.hostname, measurement.id, measurement.stamp
order by	device.hostname, measurement.id;
