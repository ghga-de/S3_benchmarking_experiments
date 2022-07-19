// Copyright 2022 Universität Tübingen, DKFZ and EMBL
// for the German Human Genome-Phenome Archive (GHGA)
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

mod base_generator;
mod nucleobase;

use clap::{self, Parser};
use std::time::Instant;

use crate::base_generator::gen_content;

#[derive(Parser)]
#[clap(about)]
pub struct Cli {
    /// Approximate file size in GiB. Sets and overrides num_lines accordingly
    #[clap(short, long, value_parser)]
    size: Option<u32>,
    /// Num of non-header lines
    #[clap(short, long, value_parser, default_value_t = 1_000_000)]
    num_lines: usize,
    /// Length of each non-header line
    #[clap(short, long, value_parser, default_value_t = 80)]
    line_length: usize,
    /// file name for output. Produces example_data/<file_name>.fasta
    #[clap(short, long, value_parser, default_value = "big-file")]
    file_name: String,
}

fn main() {
    let mut args = Cli::parse();

    if let Some(size) = args.size {
        // Adjust number of lines so we get rougly the file size we want
        args.num_lines = (size as usize * 1024usize.pow(3)) / (args.line_length + 1);
    }

    let start = Instant::now();
    gen_content(&args);
    let elapsed = start.elapsed();

    println!(
        "\nFinished generation of {} lines in {}.{:0>2} seconds.",
        args.num_lines,
        elapsed.as_secs(),
        elapsed.as_millis() % 1000 / 10
    );
}
