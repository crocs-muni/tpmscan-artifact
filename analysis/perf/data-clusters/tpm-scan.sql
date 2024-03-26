select	device.id as device_id,
      	max(measurement.vendor) as vendor,
      	max(view_firmware.firmware) as firmware,
      	round(percentile_cont(0.5) within group (order by data.value)::numeric, 5) as median,
      	round(stddev(data.value)::numeric, 5) as stddev,
      	count(distinct measurement.source) as sources,
      	count(data.value) as datapoints

  from	device
  join	measurement
    on	device.id = measurement.device_id

  join	data
    on	data.measurement_id = measurement.id

  join	algorithm
    on	algorithm.id = data.algorithm_id

  join	view_firmware
    on	view_firmware.id = measurement.id

 where	algorithm.name = '%%PERF%%'
      	and %%CONSTRAINTS%%

group by	device.id
order by	median asc, stddev asc;
