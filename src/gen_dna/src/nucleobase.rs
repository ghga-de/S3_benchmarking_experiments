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

use rand::{
    distributions::{Distribution, Standard},
    Rng,
};
use std::fmt;

pub enum Nucleobase {
    A,
    C,
    G,
    T,
}

impl Nucleobase {
    pub fn to_char(&self) -> char {
        match self {
            Nucleobase::A => 'A',
            Nucleobase::C => 'C',
            Nucleobase::G => 'G',
            Nucleobase::T => 'T',
        }
    }
}

/// Allow non debug printing
impl fmt::Display for Nucleobase {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.to_char())
    }
}

/// Allows to directly sample random bases by use of rand::random::<Nucleobase>()
impl Distribution<Nucleobase> for Standard {
    fn sample<R: Rng + ?Sized>(&self, rng: &mut R) -> Nucleobase {
        // Compiler does not recognise that the combination
        // of range and enum variants is indeed exhaustiv
        match rng.gen_range(0..4) {
            0 => Nucleobase::A,
            1 => Nucleobase::C,
            2 => Nucleobase::G,
            3 => Nucleobase::T,
            _ => unreachable!(),
        }
    }
}
