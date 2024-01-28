#!/bin/false

# -- Data selection -----------------------------------------------------------

# The following are sort-of “macros” used to select data for graphs.
# Explanations are provided as comments.

# FI MU hosts: 'musa01' — 'musa26', 'nymfe01' — 'nymfe105'.
host_musa="(device.hostname like 'musa%')"
host_nymfe="(device.hostname like 'nymfe%')"

# There was probably a huge update or load on 2022-12-08 which caused spikes in
# performances on virtually all 'musa' hosts. It has never repeated since.
# The captured data on that day are therefore deemed unusable.
host_musa_clean="($host_musa and date(measurement.stamp) != '2022-12-08')"

# The 'nymfe55' host has had long-time issues with motherboard, most
# measurements are missing due to reboots, and only a few measurements were
# recovered. Those are huge outliers still, and are thus ignored.
host_nymfe_clean="($host_nymfe and device.hostname != 'nymfe55')"

# 3rd party measurements.
host_external="(not($host_musa) and not($host_nymfe))"

# 3rd party measurements contain VMWare virtualised TPMs. Those are ignored in
# some analysis as their performance tells us nothing about the real hardware.
no_vmw="(measurement.vendor not in ('VMW'))"

# All hosts excluding measurements found unusable due to measurement problems.
host_all_filtered="($host_nymfe_clean or $host_musa_clean or $host_external)"

# Data measurement continued up to year 2024, but the data in the article
# only comprise dates before 2023-07-30.
date_tpm_scan="(measurement.stamp < '2023-07-30')"

# Some newer measurements were added after reviews.
date_tpm_scan_added="(measurement.stamp > '2023-12-01')"
