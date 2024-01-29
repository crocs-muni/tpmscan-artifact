rm booltest_p256.log
for FILE in nonces/*P256*.bin; do
    booltest --top 128 --no-comb-and --only-top-comb --only-top-deg --no-term-map --topterm-heap --topterm-heap-k 256 --block 256 --log-prints "$FILE" >> booltest_p256.log
done
rm booltest_bn256.log
for FILE in nonces/*BN256*.bin; do
    booltest --top 128 --no-comb-and --only-top-comb --only-top-deg --no-term-map --topterm-heap --topterm-heap-k 256 --block 256 --log-prints "$FILE" >> booltest_bn256.log
done
rm booltest_p224.log
for FILE in nonces/*P224*.bin; do
    booltest --top 128 --no-comb-and --only-top-comb --only-top-deg --no-term-map --topterm-heap --topterm-heap-k 224 --block 224 --halving --log-prints "$FILE" >> booltest_p224.log
done
rm booltest_p384.log
for FILE in nonces/*P384*.bin; do
    booltest --top 128 --no-comb-and --only-top-comb --only-top-deg --no-term-map --topterm-heap --topterm-heap-k 384 --block 384 --log-prints "$FILE" >> booltest_p384.log
done
rm booltest_sm256.log
for FILE in nonces/*SM256*.bin; do
    booltest --top 128 --no-comb-and --only-top-comb --only-top-deg --no-term-map --topterm-heap --topterm-heap-k 256 --block 256 --log-prints "$FILE" >> booltest_sm256.log
done
