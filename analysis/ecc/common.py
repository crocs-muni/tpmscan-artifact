import fastecdsa.curve
import fastecdsa.point
from binascii import hexlify, unhexlify
import hashlib
import math
import yaml

GENERATORS = {
    "P192": fastecdsa.curve.P192.G,
    "P224": fastecdsa.curve.P224.G,
    "P256": fastecdsa.curve.P256.G,
    "P384": fastecdsa.curve.P384.G,
    "P521": fastecdsa.curve.P521.G,
    "BN256": fastecdsa.curve.Curve(
        "BN256",
        0xFFFFFFFFFFFCF0CD46E5F25EEE71A49F0CDC65FB12980A82D3292DDBAED33013,
        0,
        3,
        0xFFFFFFFFFFFCF0CD46E5F25EEE71A49E0CDC65FB1299921AF62D536CD10B500D,
        1,
        2,
    ).G,
    "BN638": fastecdsa.curve.Curve(
        "BN638",
        0x23FFFFFDC000000D7FFFFFB8000001D3FFFFF942D000165E3FFF94870000D52FFFFDD0E00008DE55C00086520021E55BFFFFF51FFFF4EB800000004C80015ACDFFFFFFFFFFFFECE00000000000000067,
        0,
        257,
        0x23FFFFFDC000000D7FFFFFB8000001D3FFFFF942D000165E3FFF94870000D52FFFFDD0E00008DE55600086550021E555FFFFF54FFFF4EAC000000049800154D9FFFFFFFFFFFFEDA00000000000000061,
        0x23FFFFFDC000000D7FFFFFB8000001D3FFFFF942D000165E3FFF94870000D52FFFFDD0E00008DE55C00086520021E55BFFFFF51FFFF4EB800000004C80015ACDFFFFFFFFFFFFECE00000000000000066,
        16,
    ).G,
    "SM256": fastecdsa.curve.Curve(
        "SM256",
        0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF,
        0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC,
        0x28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93,
        0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFF7203DF6B21C6052B53BBF40939D54123,
        0x32C4AE2C1F1981195F9904466A39C9948FE30BBFF2660BE1715A4589334C74C7,
        0xBC3736A2F4F6779C59BDCEE36B692153D0A9877CC62A474002DF32E52139F0A0,
    ).G,
}

CURVES = {
    "P192": "0x0001",
    "P224": "0x0002",
    "P256": "0x0003",
    "P384": "0x0004",
    "P521": "0x0005",
    "BN256": "0x0010",
    "BN638": "0x0011",
    "SM256": "0x0020",
}

CURVES_REVERSED = {int(v, 16): k for k, v in CURVES.items()}

ALGS = {
    "ECDSA": "0x0018",
    "ECDAA": "0x001a",
    "SM2": "0x001b",
    "ECSCHNORR": "0x001c",
}

ALGS_REVERSED = {int(v, 16): k for k, v in ALGS.items()}

CURVE_ORDER = {
    "P192": 0xFFFFFFFFFFFFFFFFFFFFFFFF99DEF836146BC9B1B4D22831,
    "P224": 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFF16A2E0B8F03E13DD29455C5C2A3D,
    "P256": 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551,
    "P384": 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFC7634D81F4372DDF581A0DB248B0A77AECEC196ACCC52973,
    "P521": 0x1FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFA51868783BF2F966B7FCC0148F709A5D03BB5C9B8899C47AEBB6FB71E91386409,
    "BN256": 0xFFFFFFFFFFFCF0CD46E5F25EEE71A49E0CDC65FB1299921AF62D536CD10B500D,
    "BN638": 0x23FFFFFDC000000D7FFFFFB8000001D3FFFFF942D000165E3FFF94870000D52FFFFDD0E00008DE55600086550021E555FFFFF54FFFF4EAC000000049800154D9FFFFFFFFFFFFEDA00000000000000061,
    "SM256": 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFF7203DF6B21C6052B53BBF40939D54123,
}


def curve_bytes(curve):
    if "P192" in curve:
        return (192 + 7) // 8
    if "P224" in curve:
        return (224 + 7) // 8
    if "P256" in curve:
        return (256 + 7) // 8
    if "P384" in curve:
        return (384 + 7) // 8
    if "P521" in curve:
        return (521 + 7) // 8
    if "BN256" in curve:
        return (256 + 7) // 8
    if "BN638" in curve:
        return (638 + 7) // 8
    if "SM256" in curve:
        return (256 + 7) // 8
    return 0


def compute_nonce(r, s, x, e, algorithm, curve, revision=1.38):
    def extract_ecdsa_nonce(n, r, s, x, e):
        # https://en.wikipedia.org/wiki/Elliptic_Curve_Digital_Signature_Algorithm
        e = int(e, 16)
        return (pow(s, -1, n) * (e + (r * x) % n) % n) % n

    def extract_ecschnorr_nonce(n, r, s, x, e):
        # https://trustedcomputinggroup.org/wp-content/uploads/TPM2.0-Library-Spec-v1.16-Errata_v1.5_09212016.pdf
        return (s - (r * x) % n) % n

    def extract_sm2_nonce(n, r, s, x, e):
        # https://crypto.stackexchange.com/questions/9918/reasons-for-chinese-sm2-digital-signature-algorithm
        return (s + (s * x) % n + (r * x) % n) % n

    def extract_ecdaa_nonce(n, r, s, x, e):
        # https://trustedcomputinggroup.org/wp-content/uploads/TCG_TPM2_r1p59_Part1_Architecture_pub.pdf
        hasher = hashlib.sha256()
        hasher.update(
            int.to_bytes(r, byteorder="big", length=math.ceil(math.log2(n) / 8))
        )
        hasher.update(unhexlify(e))
        h = int.from_bytes(hasher.digest(), byteorder="big") % n
        return (s - h * x) % n

    nonce = {
        "ECDSA": extract_ecdsa_nonce,
        "ECSCHNORR": extract_ecschnorr_nonce,
        "SM2": extract_sm2_nonce,
        "ECDAA": extract_ecschnorr_nonce if revision < 1.36 else extract_ecdaa_nonce,
    }[algorithm](CURVE_ORDER[curve], r, s, x, e)

    nonce = hexlify(
        int.to_bytes(
            nonce,
            byteorder="big",
            length=curve_bytes(curve),
        )
    )

    return nonce


def reconstruct_pk(pk, curve, sk=None):
    point = fastecdsa.point.Point(pk[0], pk[1], curve=GENERATORS[curve].curve)
    if sk is not None:
        assert sk * GENERATORS[curve] == point
    return point


def verify_signature(r, s, pk, e, algorithm, curve, revision=1.38, nonce_point=None):
    n_bytes = curve_bytes(curve)
    n = CURVE_ORDER[curve]
    g = GENERATORS[curve]

    def verify_ecdsa():
        # https://en.wikipedia.org/wiki/Elliptic_Curve_Digital_Signature_Algorithm
        s_inv = pow(s, -1, n)
        nonce_point = s_inv * int(e[: n_bytes * 2], 16) * g + r * s_inv * pk
        return nonce_point.x == r

    def verify_ecschnorr():
        # https://trustedcomputinggroup.org/wp-content/uploads/TPM2.0-Library-Spec-v1.16-Errata_v1.5_09212016.pdf
        nonce_point = s * g - r * pk
        x_coord = int.to_bytes(
            nonce_point.x, byteorder="big", length=curve_bytes(curve)
        )

        hasher = hashlib.sha256()
        if revision >= 1.33:
            hasher.update(x_coord)
            hasher.update(unhexlify(e))
        else:
            hasher.update(unhexlify(e))
            while x_coord[0] == 0:
                x_coord = x_coord[1:]
            hasher.update(x_coord)

        r_prime = hasher.digest()
        if revision >= 1.33 and len(r_prime) > n_bytes:
            r_prime = r_prime[:n_bytes]
        r_prime = int.from_bytes(r_prime, byteorder="big") % n
        return r == r_prime

    def verify_sm2():
        # https://crypto.stackexchange.com/questions/9918/reasons-for-chinese-sm2-digital-signature-algorithm
        # return (s + (s * pk) % n + (r * pk) % n) % n
        return True

    def verify_ecdaa():
        # https://trustedcomputinggroup.org/wp-content/uploads/TCG_TPM2_r1p59_Part1_Architecture_pub.pdf
        if nonce_point is None:
            print("No nonce point provided, cannot verify ECDAA signature")
            return True

        if revision >= 1.36:
            hasher = hashlib.sha256()
            hasher.update(
                int.to_bytes(r, byteorder="big", length=math.ceil(math.log2(n) / 8))
            )
            hasher.update(unhexlify(e))
            t = int.from_bytes(hasher.digest(), byteorder="big") % n
        else:
            t = r

        return s * g - t * pk == fastecdsa.point.Point(
            nonce_point[0], nonce_point[1], curve=GENERATORS[curve].curve
        )

    return {
        "ECDSA": verify_ecdsa,
        "ECSCHNORR": verify_ecschnorr,
        "SM2": verify_sm2,
        "ECDAA": verify_ecdaa,
    }[algorithm]()


def get_device_info(results_path):
    with open(results_path, "r") as f:
        results = yaml.safe_load(f)
        manufacturer = (
            results["Manufacturer"] if "Manufacturer" in results else "unknown"
        )
        firmware = (
            results["Firmware version"] if "Firmware version" in results else "0.0.0.0"
        )
        try:
            revision = float(
                results["Capability_properties-fixed"]["TPM2_PT_REVISION"]["value"]
            )
        except KeyError:
            revision = 0.0

    return {"manufacturer": manufacturer, "firmware": firmware, "revision": revision}


def test_compute_nonce():
    r = 0x553E725A60F7D0CB564C1AD8CAE266C69E58ADB6D01741256A7351045BF18FBB
    s = 0xB795658C1CFB888D999BBDE3D40773523DD0B9A3C3B534FBE46F7FB7D99F798D
    x = 0x65EF0315E9FDFDDDB80722952E427FCA2729762B0406DE8F9A7C3B7013B29329
    e = "0000000000000000000000000000000000000000000000000000000000000000"

    assert (
        compute_nonce(r, s, x, e, "ECDAA", "P256", 1.59)
        == b"7edd1534bd14dd5040da9f19707588db808e2e53250c4951ab1c4ba9f77892d8"
    )
