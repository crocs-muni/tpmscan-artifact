# RSA visualizations

This folder contains the notebook used to create the RSA visualizations.

To successfully run it, you need to install a set of dependencies in the `algtest-pyprocess` python package. It contains a set of scripts to parse some of the `tpmscan-dataset` files and is used in the notebook `rsa.ipynb` to produce visualizations.

## Installation

First, you optionally set up a virtual environment.

```
python -m venv venv
source venv/bin/activate
```

Then install the `algtest-pyprocess` package, which should work with Python 3.10 or newer.

```
pip install -e ./algtest-pyprocess
```

If you do not have the `jupyter` installed you need to install the jupyter python package.

```
pip install jupyter
```

Now you should be able to run `jupyter` and open the notebook.

```
jupyter-lab &
```