# TPMScan analysis scripts

This directory contains scripts used to analyze the dataset and produce outputs used in the paper.

Run the following commands before inspecting individual notebooks:

```
python -m venv venv
source venv/bin/activate
pip install ./algtest-pyprocess notebook pyyaml fastecdsa pandas matplotlib ipykernel
python -m ipykernel install --user --name venv
bash preprocess.sh # preprocesses outputs for rsa and timeline notebooks
jupyter notebook
```

## ECC analysis

The `ecc` directory contains scripts used to analyse collected ECC keys and signatures.

The `keys.ipynb` notebook creates `keys/` directory with concatenation of all generated keys for further analysis, and `keys_plots/` directory with plots showing timing dependency of private key significant bit length on key generation time for some firmwares.

The `nonces.ipynb` notebook creates `nonces/` directory with concatenations of all collected nonces for further analysis, `nonces_plots/` directory with plots showing timing dependency of nonce significant bit length on signing time for some firmwares, and outputs `ecc-timing.pdf` plot showing the selected results presented in the paper.

The `inspect_nonces.ipynb` notebook serves as a way for closer inspection of selected nonce samples. The notebook loads nonce samples from the `nonces/` directory, created by the `nonces.ipynb`, so please run it first.

## RSA analysis

The `rsa` folder contains the notebook used to create the RSA visualizations.

The `rsa.ipynb` notebook outputs the EK and RSK visualizations used in the paper.

## Algorithm support analysis

The `support` directory contains scripts used to analyze collected operation support information.

The `support.ipynb` notebook loads the operation support information from the dataset, normalizes it by firmware versions, and outputs statistics presented in the paper.

## Firmware version timeline

The `timeline` directory contains jupyter notebook `timeline.ipynb` used to prepare the basis of the firmware version timeline. Note that this figure involved a lot of manual editing.

## Helper package algtest-pyprocess

The directory `algtest-pyprocess` contains a helper package that can prepare certain outputs used in `rsa` and `timeline` scripts.
