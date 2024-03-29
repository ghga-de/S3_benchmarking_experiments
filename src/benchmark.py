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
"""Functionality to benchmark up-/download for different S3 endpoints"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

from ghga_connector.core.file_operations import (  # type: ignore
    download_file_parts,
    read_file_parts,
    upload_file_part,
)
from ghga_connector.core.retry import WithRetry  # type: ignore
from hexkit.providers.s3.testutils import (  # type: ignore
    S3ConfigBase,
    S3ObjectStorage,
    config_from_localstack_container,
)
from testcontainers.localstack import LocalStackContainer  # type: ignore

DATA_DIR = Path(__file__).parent.parent.resolve() / "example_data"
OBJECT_IDS = [fasta for fasta in os.listdir(DATA_DIR) if fasta.endswith(".fasta")]
FILE_PATHS = [DATA_DIR / fasta for fasta in OBJECT_IDS]
PART_SIZE = 16 * 1024 * 1024


def main():
    """Argument parsing and checking of correct environment files"""
    bucket_id = "ghga-file-io-benchmarking"
    cos = DATA_DIR / "s3_cos.env"
    ceph = DATA_DIR / "s3_ceph.env"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target", "-t", choices=["ceph", "cos", "localstack"], default="localstack"
    )
    args = parser.parse_args()

    if args.target == "localstack":
        asyncio.run(benchmark_localstack(bucket_id=bucket_id))
    elif args.target == "cos":
        if not cos.exists():
            raise FileNotFoundError(cos)
        # different bucket name for now, until we get the proper one
        asyncio.run(
            benchmark_remote(config=S3ConfigBase(cos), bucket_id="ghga-permanent")
        )
    elif args.target == "ceph":
        if not ceph.exists():
            raise FileNotFoundError(ceph)
        asyncio.run(benchmark_remote(config=S3ConfigBase(ceph), bucket_id=bucket_id))


async def benchmark_remote(config: S3ConfigBase, bucket_id=str):
    """Run against a remote endpoint based on the given config"""
    WithRetry.set_retries(4)
    storage = S3ObjectStorage(config=config)
    await run_benchmark(object_storage=storage, bucket_id=bucket_id)


async def benchmark_localstack(bucket_id: str):
    """Create bucket and run up-/download benchmarks"""
    # assume localstack should be fairly reliable
    WithRetry.set_retries(0)
    with LocalStackContainer(image="localstack/localstack:0.14.2").with_services(
        "s3"
    ) as localstack:
        config = config_from_localstack_container(localstack)
        storage = S3ObjectStorage(config=config)
        await storage.create_bucket(bucket_id)
        await run_benchmark(object_storage=storage, bucket_id=bucket_id)
        await storage.delete_bucket(bucket_id)


async def run_benchmark(object_storage: str, bucket_id: str):
    """Delegate running up-/donwload"""
    for path, object_id in zip(FILE_PATHS, OBJECT_IDS):
        await benchmark_upload(
            object_storage=object_storage, bucket_id=bucket_id, path=path
        )
        await benchmark_download(
            object_storage=object_storage, bucket_id=bucket_id, object_id=object_id
        )


async def benchmark_upload(object_storage: S3ObjectStorage, bucket_id: str, path: Path):
    """Call and time actual upload per file"""
    print(f"Uploading file {path}")
    upload_start = time.time()
    await upload_object(object_storage=object_storage, bucket_id=bucket_id, path=path)
    elapsed = time.time() - upload_start
    print(f"Upload for file {path} finished in {elapsed:.2f}s")


async def upload_object(object_storage: S3ObjectStorage, bucket_id: str, path: Path):
    """Run and time upload of all parts"""
    object_id = os.path.basename(path)
    upload_id = await object_storage.init_multipart_upload(
        bucket_id=bucket_id, object_id=object_id
    )

    upload_start = time.time()
    total_parts = 0
    try:
        with open(path, "r+b") as source:
            for (part_number, file_part) in enumerate(
                read_file_parts(source, part_size=PART_SIZE), start=1
            ):
                part_upload_url = await object_storage.get_part_upload_url(
                    upload_id=upload_id,
                    bucket_id=bucket_id,
                    object_id=object_id,
                    part_number=part_number,
                )
                upload_file_part(presigned_url=part_upload_url, part=file_part)

                duration = time.time() - upload_start
                average = part_number * (PART_SIZE / 1024**2) / duration
                print(
                    f"\rAverage transfer rate: {average:.2f} MiB/s (Part number {part_number})",
                    end="",
                )
                total_parts = part_number
    except (Exception, KeyboardInterrupt) as exc:  # pylint: disable=bare-except
        # clean up multipart upload for next try, if we run into issues
        # makes running this in a loop easier
        await object_storage.abort_multipart_upload(
            upload_id=upload_id, bucket_id=bucket_id, object_id=object_id
        )
        print(f"\nMultipart upload {upload_id} aborted", file=sys.stderr)
        raise exc
    print("\nCompleting multipart upload")
    await object_storage.complete_multipart_upload(
        upload_id=upload_id,
        bucket_id=bucket_id,
        object_id=object_id,
        anticipated_part_quantity=total_parts,
        anticipated_part_size=PART_SIZE,
    )


async def benchmark_download(
    object_storage: S3ObjectStorage, bucket_id: str, object_id: str
):
    """Call and time actual download per file"""
    print(f"Downloading object {object_id}")
    upload_start = time.time()
    await download_object(
        object_storage=object_storage, bucket_id=bucket_id, object_id=object_id
    )
    elapsed = time.time() - upload_start
    print(f"Download for object {object_id} finished in {elapsed:.2f}s")


async def download_object(
    object_storage: S3ObjectStorage, bucket_id: str, object_id: str
):
    """Run and time download of all parts"""
    input_path = DATA_DIR / object_id
    file_size = input_path.stat().st_size
    download_url = await object_storage.get_object_download_url(
        bucket_id=bucket_id, object_id=object_id
    )
    file_parts = download_file_parts(
        download_url=download_url, part_size=PART_SIZE, total_file_size=file_size
    )

    output_path = DATA_DIR / input_path.name.replace(".fasta", "_dl.fasta")
    download_start = time.time()

    with open(
        output_path,
        "wb",
        buffering=PART_SIZE,
    ) as target:
        for (part_number, file_part) in enumerate(file_parts, start=1):
            target.write(file_part)

            duration = time.time() - download_start
            average = part_number * (PART_SIZE / 1024**2) / duration
            print(
                f"\rAverage transfer rate: {average:.2f} MiB/s (Part number {part_number})",
                end="",
            )
    print("\nRunning cleanup ...")
    await object_storage.delete_object(bucket_id=bucket_id, object_id=object_id)
    os.remove(output_path)


if __name__ == "__main__":
    main()
