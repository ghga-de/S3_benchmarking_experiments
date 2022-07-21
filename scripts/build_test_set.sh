#!/bin/bash

set -e

cd ../src/gen_dna
cargo build --release
for size in 10 50 150; do ./target/release/gen_dna --file-name "$size"G --size $size; done
