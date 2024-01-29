# TPMScan Artifact

This repository contains the artifact to paper *TPMScan: A wide-scale study of security-relevant properties of TPM 2.0 chips* accepted to CHES 2024.

```bash
git clone --recursive https://github.com/crocs-muni/tpmscan-artifact
```

The structure of the artifact is following:

- `analysis` directory contains scripts and jupyter notebooks used for producing outputs presented in the paper
- `attack` directory contains proof-of-concept implementation of the attack using only 9 signatures created by a TPM with certain Intel fTPM versions to recover the private key used to produce those signatures
- `tpmscan-dataset` directory contains a curated dataset collected by the `tpm2-algtest` tool (also available at https://github.com/crocs-muni/tpmscan-dataset)
- `tpm_pcr_data` directory contains the data collected by the `tpm_pcr` tool used for EK and SRK analysis and firmware version timeline
- `tpm2-algtest` directory contains the implementation of the data collection tool `tpm2-algtest` (also available at https://github.com/crocs-muni/tpm2-algtest)
- `tpm_pcr` directory contains the implementation of the data collection tool `tpm_pcr` (also available at https://github.com/petrs/TPM_PCR)
