#!/bin/bash
cd algtest-pyprocess
python -m pyprocess tpm metadata-update ../../tpmscan-dataset
python -m pyprocess tpm summary-create ./metadata.json --tpm-pcr-path ../../tpm_pcr_data
