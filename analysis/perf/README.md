# TPM Graphs

A tool to create various graphs from TPM measurements captured by
[TPM2 Algtest](https://github.com/crocs-muni/tpm2-algtest).

The program can read ZIP files to create performance graphs. It can also utilise
database for more complex statistics, e.g. scatter or box plots for medians.


## How to reproduce TPMScan paper's Figure 6

### Data Sources

Measurements from the dataset can be prepared by running script
`prepare_data.sh` and output to the `data` directory (the script requires
`zip` installed).

Other measurements from university machines can be found on this address:
https://drive.google.com/drive/folders/1E2KtHnZ1S_wqoHY4DZ9gMAReZHIQZauy?usp=drive_link

### Containers

Using `docker compose`, one can reproduce the results using the scenario
provided in `compose.yaml`.

1. Ensure `docker` and `docker compose` are installed.

2. Ensure `data` directory with selected measurements exist (see the section
   above).

   Alternatively, it is possible to add a volume to `compose.yaml` into the
   `shell` service, for example:

       ```yaml
       volumes:
         - "./:/tpm-graphs"
         - "$MEASUREMENTS:/data"  # Add this line
       ```

   Replace `$MEASUREMENTS` with a full path to the directory with ZIP files
   of measurements to be loaded.

   The directory will be available as `/data` in the container rather than
   `/tpm-graphs/data`. The scenario will inspect both locations.

3. Run `docker compose up --abort-on-container-exit` in the directory with
   `compose.yaml` file.

3. Once everything is set up, the script will automatically load all
   sources from `/tpm-graphs/data` or `/data` in the container, and then
   it will proceed to re-create performance graphs from the paper.

   This operation can take a lot of time, especially for the entire dataset.
   Thus it is recommended not to destroy volumes for the containers. Especially
   `postgres` can reuse the existing volume to avoid re-loading the dataset.

4. Outputs will be placed in the `results` directory, which will be visible
   outside of the container in the directory with the script.

   `*.pdf` files contain raw graphs, `*.txt` files contain point metadata,
   including firmware versions, that was then used to manually annotate graphs
   in Inkscape.

To clean up containers and volumes, use `docker compose down`.

### Manual

Here follows a step-by-step list of instructions to reproduce Figure 6 and
version labels from the TPMScan paper manually.

There are many optional steps which were found useful to speed up debugging and
generating graphs. They should not be necessary, but their omission can make
the process much slower.

1. Install Python dependencies from `requirements.txt`. If using `pip` in
   a virtual environment, run `pip install -r requirements.txt`.

2. Install PostgreSQL and create a `tpm` database for the current user `$USER`.
   Usually, as `root`, run `psql -U postgres` and execute (replacing `$USER`
   with a real user login):

      ```sql
      create database tpm;
      alter database tpm set owner to $USER;
      ```

   Alternative database name can also be used by setting `export TPM_DB_URL="postgresql://..."`
   environment variables for all of the following commands.

3. Obtain measurement dataset (see section above) and store it in the `data`
   directory.

4. (Optional) Populate the database and drop all indices and constraints to
   speed up loading of the entire dataset.

      ```sh
      ./tpm-graphs-db
      psql -d "$TPM_DB_URL" -1 -f sql/indices-drop.sql
      psql -d "$TPM_DB_URL" -1 -f sql/contraints-drop.sql
      ```

5. (Optional) Re-create table `data` with partitioning on `LIST (device_id)`,
   which should speed up graph generation significantly.

   Unfortunately, there is no easy automated way to do this -- SQLAlchemy
   requires a primary key, which must then appear in the partition list, thus
   it cannot create partitioned table out of the box.

   This has to be fixed manually: rename `data` do `data_old`, re-create it
   **without** primary key, with partitioning on `LIST (device_id)` and
   a default partition. Then simply copy data from `data_old` and delete the
   old table.

6. Load all measurements into the database. This can take up to several hours.

      ```sh
      find data -name '*.zip' | ./tpm-graphs-db db.read -
      ```

7. (Optional) If you dropped indices and constraints in previous steps, restore
   them now.

      ```sh
      psql -d "$TPM_DB_URL" -1 -f sql/constraints-setup.sql
      psql -d "$TPM_DB_URL" -1 -f sql/indices-setup.sql
      ```

8. Setup additional views and functions used for graph creation and analysis.

      ```sh
      psql -d "$TPM_DB_URL" -1 -f sql/version.sql
      psql -d "$TPM_DB_URL" -1 -f sql/view-setup.sql
      ```

9. (Optional) If you created table partitions, re-partition the data
    using `scripts/partition.pl`.

10. Finally, create graphs and data clusters from the paper. A convenience
    script has been provided.

      ```sh
      ./tpm-scan-graphs
      ```

   Files will be written into `results` directory as with the Docker Compose
   method described above.

## Dependencies

The dependencies are listed in `requirements.txt`. Preferably install these
from your system repository.

If that is not possible or there are no such packages, use `pip` in virtual
environment:

   ```sh
   python -mvenv env
   source env/bin/activate
   pip install -r requirements.txt
   ```


## Database setup

A database is required in order to compute scatter and box plots. PostgreSQL is
recommended, **other database engines were not tested**. The database
is populated the first time `tpm-graphs` is executed with `--db` option
and a valid database connection. Running the command with no other arguments
should be sufficient.

SQLAlchemy creates the basic database layout. In addition, the following
optimisations (especially for huge datasets) are recommended:

* Partition `data` table for devices. Use `scripts/partition.pl` script each
  time a new host is added to the `device` table.

* Create B-tree indices for every column in `data`.

* There is a materialised view utilised by some parts of the script.
  SQLAlchemy can use these views, but it is difficult to create them out of the
  box. Therefore, run this after creating the database (see `sql/view-setup.sql`):

      create materialized view view_algorithms as
      select distinct measurement_id, algorithm_id from data

  It is recommended to add indices on this view as well.


## Database tweaks

### Loading initial data

Loading a huge amount of data into the database is slow. The following
might make it faster:

* Drop all constraints on `data`.
* Drop all indices on `data`.

When data are loaded, restore all constraints and indices and call `analyze`.

See `sql` directory with prepared queries, e.g.

    psql -d "$TPM_DB_URL" -1Atq -f sql/drop-constraints.sql

### Adding new data

Just run the `db.read` command of the script. The command should be run
regularly as new measurements are obtained, because adding too much data at the
same time will be slow.

After adding all data, run

    psql -d "$TPM_DB_URL" -1A -e 'refresh materialized view view_algorithms'

to update the materialized view.

If a new host was added, it is recommended to create a partition for it under
the `data` table if partitions were enabled. The `scripts/partition.pl` should
take care of that.
