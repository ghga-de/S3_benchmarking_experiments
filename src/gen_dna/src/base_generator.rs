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

use crate::Cli;
use rand;
use std::{
    fs::{self, File},
    io::{prelude::*, BufWriter},
    path::PathBuf,
    time::{Duration, Instant},
};

use crate::nucleobase::Nucleobase;

/// Writes header and lines of random bases to an output file
pub fn gen_content(args: &Cli) {
    let start = Instant::now();

    let out_dir = "../../example_data";

    fs::create_dir_all(&out_dir).expect("Could not create output directory.");

    // build complete output file path
    let mut path = PathBuf::from(&out_dir);
    path.push(&args.file_name);
    path.set_extension(&"fasta");

    // we need a buffered writer, else this gets really slow
    // initialising using with_capacity might help if buffer is too small
    let mut target = BufWriter::new(File::create(path.as_path()).expect("Could not create file."));

    // header
    target
        .write(b"> Dinosaur DNA")
        .expect("Failed writing header to file.");

    // draw bases for next line and write to file
    for idx in 0..args.num_lines as usize {
        progress(idx, start.elapsed(), args.num_lines);
        target
            .write(gen_random_sequence(args.line_length).as_bytes())
            .expect("Failed writing sequence to file.");
    }
}

/// Draw bases for a line and return line
fn gen_random_sequence(line_length: usize) -> String {
    let mut seq: Vec<char> = Vec::with_capacity(line_length + 1);
    seq.push('\n');

    // fill buffer with random bases
    for _ in 1..=line_length {
        seq.push(rand::random::<Nucleobase>().to_char());
    }
    String::from_iter(&seq)
}

/// Basic information percentage completed and time elapsed
fn progress(idx: usize, elapsed: Duration, num_lines: usize) {
    // Only really relevant for large files
    // skip most lines, else this becomes a bottleneck
    if idx % 100_000 == 0 {
        print!(
            "\r{:.2}% ({}.{:0>2}s)",
            idx as f32 / num_lines as f32 * 100.0,
            elapsed.as_secs(),
            elapsed.as_millis() % 1000 / 10,
        );
        std::io::stdout().flush().unwrap();
    }
}
