#!/bin/bash

# Copyright 2022 Universität Tübingen, DKFZ and EMBL
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e

workspace=$(dirname $(dirname $(readlink -f "$0")))

cd "$workspace"/src/gen_dna
cargo build --release
./target/release/gen_dna --file-name 4M --size 4M
for size in 10 50 150; do ./target/release/gen_dna --file-name "$size"G --size "$size"G; done
