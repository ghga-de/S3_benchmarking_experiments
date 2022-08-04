#!/bin/bash

set -e

workspace=$(dirname $(dirname $(readlink -f "$0")))

cd "$workspace"/src/gen_dna
cargo build --release
./target/release/gen_dna --file-name 4M --size 4M
for size in 10 50 150; do ./target/release/gen_dna --file-name "$size"G --size "$size"G; done
