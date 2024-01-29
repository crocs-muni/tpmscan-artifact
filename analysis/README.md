# TPMScan analysis scripts

This directory contains scripts used to analyze the dataset and produce outputs used in the paper.

Run the following commands before inspecting individual notebooks:

```bash
python -m venv venv
source venv/bin/activate
pip install ./algtest-pyprocess notebook pyyaml fastecdsa pandas matplotlib ipykernel booltest
python -m ipykernel install --user --name venv
bash preprocess.sh # preprocesses outputs for rsa and timeline notebooks
jupyter notebook
```

## Certificate analysis

The `certs` directory contains Jupyter notebook used for producing **Figure 1**.

Before running the script, download preprocessed CC and FIPS certificates from https://drive.google.com/file/d/1kjnwSdBmoUrK4croKmP5ELmWzXRnuxMz/view?usp=drive_link and extract them to the `certs` directory.

## Firmware version timeline

The `timeline.ipynb` notebook is used to prepare the basis of the firmware version timeline **Figure 2**. Note that this figure involved a lot of manual editing.

## ECC analysis

The `keys.ipynb` notebook creates `keys/` directory with concatenation of all generated keys for further analysis, and `keys_plots/` directory with plots showing timing dependency of private key significant bit length on key generation time for some firmwares.

The `nonces.ipynb` notebook creates `nonces/` directory with concatenations of all collected nonces for further analysis, `nonces_plots/` directory with plots showing timing dependency of nonce significant bit length on signing time for some firmwares, and outputs `ecc-timing.pdf` plot showing the selected findings presented in **Figure 3**.

The `inspect_nonces.ipynb` notebook serves as a way for closer inspection of selected nonce samples. The notebook loads nonce samples from the `nonces/` directory, created by the `nonces.ipynb`, so please run it first.

## RSA analysis

The `rsa.ipynb` notebook outputs the EK and RSK visualizations used in the paper (**Figure 4** and **Figure 5**).

## Algorithm support analysis

The `support.ipynb` notebook loads the operation support information from the dataset, normalizes it by firmware versions, and outputs statistics presented in the paper.

## Performance analysis

The `perf` directory contains script used to analyze measured operation performance and produce **Figure 6**. This analysis involves large amount of data so more complex setup is required, please refer to the [README.md](perf/README.md) in the `perf` directory.