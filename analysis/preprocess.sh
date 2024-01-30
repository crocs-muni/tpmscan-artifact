#!/bin/bash
pyprocess tpm metadata-update ../tpmscan-dataset
pyprocess tpm summary-create ./metadata.json --tpm-pcr-path ../tpm_pcr_data
