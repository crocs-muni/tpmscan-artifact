# TPMScan Artifact

This repository contains artifacts to paper *TPMScan: A wide-scale study of security-relevant properties of TPM 2.0 chips* accepted to CHES 2024.

The structure of the artifact is following:

- the `/tpmscan-dataset` directory contains the main dataset collected by tpm2-algtest tool (also available at https://github.com/crocs-muni/tpmscan-dataset)
- the `/tpm_pcr_data` directory contains the data collected by `tpm_pcr` tool
- the `/analysis` directory contains Jupyter notebooks used for producing outputs presented in the paper
- the `/attack` directory contains proof-of-concept implementation of the attack using only 9 signatures created by a TPM with certain Intel fTPM versions to recover the private key
- the `/tpm2_algtest` directory contains the latest version of the `tpm2-algtest` tool (also available at https://github.com/crocs-muni/tpm2-algtest)
- the `/tpm_pcr` directory contains the latest version of `tpm_pcr` tool (also available at https://github.com/petrs/TPM_PCR)
