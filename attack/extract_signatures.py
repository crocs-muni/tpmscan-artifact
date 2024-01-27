import os
import yaml
import csv
from pathlib import Path

DATASET_PATH = "../tpmscan-dataset"

CURVES = {
    "0x0001": "P192",
    "0x0002": "P224",
    "0x0003": "P256",
    "0x0004": "P384",
    "0x0005": "P521",
    "0x0010": "BN256",
    "0x0011": "BN638",
    "0x0020": "SM256",
}

ALGS = {
    "0x0018": "ECDSA",
    "0x001a": "ECDAA",
    "0x001b": "SM2",
    "0x001c": "ECSCHNORR",
}


def main():
    for sample in Path(DATASET_PATH).rglob("Cryptoops_Sign:ECC_*.csv"):
        with open(sample.parent.parent.joinpath("results.yaml"), "r") as f:
            info = yaml.safe_load(f)

        manufacturer = info["Manufacturer"]
        fw = info["Firmware version"]
        curve = CURVES[sample.name.split("_")[2]]
        alg = ALGS[sample.name.split("_")[3].split(".")[0]]
        identifier = sample.parent.parent.name

        os.makedirs(f"signatures/", exist_ok=True)
        signatures = []
        with open(sample, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                signatures.append(
                    {
                        "r": row["signature_r"],
                        "s": row["signature_s"],
                        "m": row["digest"],
                        "pk": "04" + row["public_key_x"] + row["public_key_y"],
                    }
                )
        with open(
            f"signatures/{manufacturer}_{fw}_{curve}_{alg}_{identifier}.csv", "w"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=["r", "s", "m", "pk"])
            writer.writeheader()
            writer.writerows(signatures)


if __name__ == "__main__":
    main()
