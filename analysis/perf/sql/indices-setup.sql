create index ix_data_measurement_id on data using btree (measurement_id);
create index ix_data_algorithm_id on data using btree (algorithm_id);
analyze;
