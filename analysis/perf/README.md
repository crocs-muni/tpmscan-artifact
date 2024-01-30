# TPM Graphs

A tool to create various graphs from TPM measurements captured by
[TPM2 Algtest](https://github.com/crocs-muni/tpm2-algtest).

The program can read ZIP files to create performance graphs. It can also utilise
database for more complex statistics, e.g. scatter or box plots for medians.

A step-by-step guide to recreate Figure 6 from the TPM Scan paper is included
in the last section of this document.


## Dependencies

The following Python modules are required:

* `numpy`
* `sqlalchemy` (for database)
* `dogpile-cache` (for database)

Install preferably from your system repository. If that is not possible or
there are no such packages, use `pip` as follows:

    pip3 install --user --break-system-packages ${PACKAGES...}

The following modules are recommended for `mypy`:

* `data-science-types`
* `types-PyYAML`


## Database setup

An database is required in order to compute scatter and box plots. PostgreSQL is
recommended, **other database engines were not tested**.

SQLAlchemy creates the basic database layout. In addition, the following
optimisations (especially for huge datasets) are recommended:

* Table partitions for `data`. Use `scripts/partition.pl` script each time a new
  host is added to the `device` table.

* Create B-tree indices for every column in `data`.

* There is a materialised view utilised by some parts of the script.
  SQLAlchemy can use these views, but it is difficult to create them out of the
  box. Therefore, run this when creating the database:

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

    psql -dtpm -1A -f sql/drop-constraints.sql

### Adding new data

Just run the `db.read` command of the script. The command should be run
regularly, as adding too much data at the same time will be slow.

After adding all data, run

    psql -dtpm -1A -e 'refresh materialized view view_algorithms'

to update the materialized view.

If a new host was added, it is recommended to create a partition for it under
the `data` table. The `scripts/partition.pl` should take care of that.


## How to reproduce TPMScan paper's Figure 6

Here follows a step-by-step list of instructions to reproduce Figure 6 and
version labels from the TPMScan paper.

There are many optional steps which were found useful to speed up graph
generation process. They should not be necessary, but their omission may result
in the graph generation to be very slow.

1. Install `dogpile-cache`, `psycopg2`, `sqlalchemy` and `numpy` python packages (these are already installed in the `venv` recommended for analysis notebooks).

2. Install PostgreSQL and create a `tpm` database for the current user `$USER`.

      ```sql
      create database tpm;
      alter database tpm set owner to $USER;
      ```

   Alternative database name can also be used by setting `export DATABASE=name`
   environment variable for all of the following commands.

3. Create `cache` directory if it does not exist already.

4. Obtain measurement files and save them to directory `./data`.
   - Measurements from the dataset can be prepared by running script `prepare_data.sh` and output to the `data` directory (the script requires `zip` installed).
   - Other measurements from university machines can be found on this address: https://drive.google.com/drive/folders/1E2KtHnZ1S_wqoHY4DZ9gMAReZHIQZauy?usp=drive_link

5. (Optional) Populate the database with a single measurement and drop all
   indices and constraints to speed up loading of the entire dataset.

      ```sh
      ls data/*.zip | head -1 | ./tpm-graphs-db db.read -
      psql -d "${DATABASE:-tpm}" -1 -f sql/indices-drop.sql
      psql -d "${DATABASE:-tpm}" -1 -f sql/contraints-drop.sql
      ```

6. (Optional) Re-create table `data` with partitioning on `LIST (device_id)`,
   which should speed up graph generation significantly.

   Unfortunately, there is no easy automated way to do this -- SQLAlchemy
   requires a primary key, which must then appear in the partition list, thus
   it cannot create partitioned table out of the box.

   This has to be fixed manually: rename `data` do `data_old`, re-create it
   **without** primary key, with partitioning on `LIST (device_id)` and
   a default partition. Then simply copy data from `data_old` and delete the
   old table.

7. Load all measurements into the database. This can take up to several hours.

      ```sh
      ls data/*.zip | ./tpm-graphs-db db.read -
      ```

8. (Optional) If you dropped indices and constraints in previous steps, restore
   them now.

      ```sh
      psql -d "${DATABASE:-tpm}" -1 -f sql/constraints-setup.sql
      psql -d "${DATABASE:-tpm}" -1 -f sql/indices-setup.sql
      ```

9. Setup additional views and functions used for graph creation and analysis.

      ```sh
      psql -d "${DATABASE:-tpm}" -1 -f sql/version.sql
      psql -d "${DATABASE:-tpm}" -1 -f sql/view-setup.sql
      ```

10. (Optional) If you created table partitions, you re-partition the data
    using `scripts/partition.pl`.

11. Finally, create graphs and data clusters from the paper. A convenience
   script has been provided.

      ```sh
      ./tpm-scan-graphs
      ```

    Files will be written into `results` directory. `*.pdf` files contain
    raw graphs, `*.txt` files contain point metadata, including firmware
    versions, that was then used to manually annotate graphs in Inkscape.
