alter table data
  add constraint data_algorithm_id_fkey
  foreign key (algorithm_id) references algorithm(id)
  on delete cascade;

alter table data
  add constraint data_device_id_fkey
  foreign key (device_id) references device(id)
  on delete cascade;

alter table data
  add constraint data_measurement_id_fkey
  foreign key (measurement_id) references measurement(id)
  on delete cascade;
