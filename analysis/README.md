# TPMScan analysis scripts

This directory contains scripts used to analyze the dataset and produce outputs used in the paper.

## ECC analysis

The `ecc` directory contains scripts used to analyse collected ECC keys and signatures.

**Requirements:** Python 3.8 or newer, matplotlib, pandas, fastecdsa, pyyaml, jupyter notebook

The `keys.ipynb` notebook creates `keys/` directory with concatenation of all generated keys for further analysis, and `keys_plots/` directory with plots showing timing dependency of private key significant bit length on key generation time for some firmwares.

The `nonces.ipynb` notebook creates `nonces/` directory with concatenations of all collected nonces for further analysis, `nonces_plots/` directory with plots showing timing dependency of nonce significant bit length on signing time for some firmwares, and outputs `ecc-timing.pdf` plot showing the selected results presented in the paper.

The `inspect_nonces.ipynb` notebook serves as a way for closer inspection of selected nonce samples. The notebook loads nonce samples from the `nonces/` directory, created by the `nonces.ipynb`, so please run it first.

## Algorithm support analysis

The `support` directory contains scripts used to analyse collected operation support information.

**Requirements:** Python 3.8 or newer, pandas, pyyaml, jupyter notebook

The `support.ipynb` notebook loads the operation support information from the dataset, normalizes it by firmware versions, and outputs statistics presented in the paper.
