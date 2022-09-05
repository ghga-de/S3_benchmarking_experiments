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
"""Plot completion times for all objects and iterations"""

import argparse
import re
from collections import defaultdict as ddict
from pathlib import Path

import matplotlib.pyplot as plt  # type: ignore


def main():
    """Process input file and plot depending on direction (upload/download)"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--infile", "-i", type=argparse.FileType("r"))
    parser.add_argument("--name", "-n", default="benchmark")
    args = parser.parse_args()
    data = parse_time(args.infile)
    keys = data.keys()

    ul_labels = sorted([key for key in keys if "/" in key])
    ul_timing = [data[label] for label in ul_labels]
    ul_labels = [label.rpartition("/")[2] for label in ul_labels]
    plot(ul_labels, ul_timing, "upload", args.name)

    dl_labels = sorted([key for key in keys if "/" not in key])
    dl_timing = [data[label] for label in dl_labels]
    plot(dl_labels, dl_timing, "download", args.name)


def parse_time(file):
    """Convert log lines to dict for objects and direction"""
    data = ddict(list)
    dl_time = re.compile(r"Download for object (?P<obj>.*) finished in (?P<time>.*)s")
    ul_time = re.compile(r"Upload for file (?P<file>.*) finished in (?P<time>.*)s")
    for line in file.readlines():
        if line.startswith("Average transfer rate"):
            continue
        line = line.strip()
        match = dl_time.match(line)
        if match:
            data[match.group("obj")].append(float(match.group("time")))
        match = ul_time.match(line)
        if match:
            data[match.group("file")].append(float(match.group("time")))
    return data


def plot(labels: list[str], timing: list[list[float]], direction: str, name: str):
    """Plot timimings for all objects for one direction"""

    out_dir = Path(__file__).parent.parent / "output"
    if not out_dir.exists():
        out_dir.mkdir()

    for label, vals in zip(labels, timing):
        if len(vals) > 50:
            xticks = list(range(1, len(vals) + 1, 10))
        elif len(vals) > 10:
            xticks = list(range(1, len(vals) + 1, 5))
        else:
            xticks = list(range(1, len(vals) + 1))

        plt.plot(range(1, len(vals) + 1), vals, "x")
        plt.xticks(xticks, xticks, rotation=30)
        plt.title(f"{label} ({direction.title()}) ({name})")
        plt.xlabel("Iteration")
        plt.ylabel("Time Elapsed [s]")
        plt.savefig(out_dir / f"{label}_{direction}_{name.lower()}.png")
        plt.clf()


if __name__ == "__main__":
    main()
