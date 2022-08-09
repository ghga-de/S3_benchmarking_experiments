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
"""TODO"""


import argparse
import re
from collections import defaultdict as ddict

import numpy as np  # type: ignore


def main():
    """TODO"""
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", type=argparse.FileType("r"), nargs="?")
    args = parser.parse_args()
    data = parse(args.infile)
    process(data)


def parse(file):
    """TODO"""
    data = ddict(list)
    file_name = re.compile(r"Uploading file (.*)")
    object_name = re.compile(r"Downloading object (.*)")
    # Assume MiB/s
    transfer_rate = re.compile(
        r"Average transfer rate: (.*) MiB/s \(Part number (\d+)\)"
    )
    current = ""
    for line in file.readlines():
        line = line.strip()
        if line.startswith("Uploading file"):
            match = file_name.match(line)
            current = match.group(1)
        elif line.startswith("Downloading object"):
            match = object_name.match(line)
            current = match.group(1)
        elif line.startswith("Average transfer"):
            match = transfer_rate.match(line)
            rate = float(match.group(1))
            data[current].append(rate)
        elif "response code 503" in line:
            data["errors"].append(line)
    return data


def process(data: dict[str, list]):
    """TODO"""
    for key, value in data.items():
        if key == "errors":
            linebreak = "\n"
            print(
                f"Number of errors: {len(value)}{linebreak}{linebreak}{linebreak.join(value)}"
            )
            continue
        if "/" in key:
            key = f"{key.rpartition('/')[2]} (Upload)"
        else:
            key = f"{key} (Download)"
        print(
            f"""{key}:
            average: {np.mean(value):.2f} +/- {np.std(value):.2f}MiB/s
            min: {np.min(value):.2f}MiB/s
            max: {np.max(value):.2f}MiB/s
            """
        )


if __name__ == "__main__":
    main()
