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
import asyncio
import filecmp
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

BUCKET_ID = "ghga-file-io-benchmarking"
DATA_DIR = Path(__file__).parent.parent.resolve() / "example_data"
OBJECT_IDS = ["1G.fasta"]
FILE_PATHS = [DATA_DIR / object_id for object_id in OBJECT_IDS]
PART_SIZE = 16 * 1024 * 1024


async def benchmark_remote(config: S3ConfigBase):
    """Run against a remote endpoint based on the given config"""
    WithRetry.set_retries(3)
    object_storage = S3ObjectStorage(config=config)
    await benchmark_upload(object_storage=object_storage)
    await benchmark_download(object_storage=object_storage)


async def benchmark_localstack():
    """Create bucket and run up-/download benchmarks"""
    WithRetry.set_retries(0)
    with LocalStackContainer(image="localstack/localstack:0.14.2").with_services(
        "s3"
    ) as localstack:
        config = config_from_localstack_container(localstack)
        storage = S3ObjectStorage(config=config)
        await storage.create_bucket(BUCKET_ID)
        await benchmark_upload(object_storage=storage)
        await benchmark_download(object_storage=storage)
        await storage.delete_bucket(BUCKET_ID)


async def benchmark_upload(object_storage: S3ObjectStorage):
    """Call and time actual upload per file"""
    for path in FILE_PATHS:
        print(f"Uploading file {path}")
        upload_start = time.time()
        await upload_object(object_storage=object_storage, path=path)
        elapsed = time.time() - upload_start
        print(f"Upload for file {path} finished in {elapsed:.2f}s")


async def upload_object(object_storage: S3ObjectStorage, path: Path):
    """TODO"""
    object_id = os.path.basename(path)
    upload_id = await object_storage.init_multipart_upload(
        bucket_id=BUCKET_ID, object_id=object_id
    )

    with open(path, "r+b") as source:
        duration = 0.0
        for (part_number, file_part) in enumerate(
            read_file_parts(source, part_size=PART_SIZE), start=1
        ):
            upload_start = time.time()
            part_upload_url = await object_storage.get_part_upload_url(
                upload_id=upload_id,
                bucket_id=BUCKET_ID,
                object_id=object_id,
                part_number=part_number,
            )
            upload_file_part(presigned_url=part_upload_url, part=file_part)
            duration = duration + time.time() - upload_start
            average = (PART_SIZE / 1024**2) / (duration / part_number)
            print(
                f"\rAverage transfer rate: {average:.2f} MiB/s (Part number {part_number})",
                end="",
            )
    print("\nCompleting multipart upload")
    await object_storage.complete_multipart_upload(
        upload_id=upload_id, bucket_id=BUCKET_ID, object_id=object_id
    )


async def benchmark_download(object_storage: S3ObjectStorage):
    """Call and time actual download per file"""
    for object_id in OBJECT_IDS:
        print(f"Downloading object {object_id}")
        upload_start = time.time()
        await download_object(object_storage=object_storage, object_id=object_id)
        elapsed = time.time() - upload_start
        print(f"Download for object {object_id} finished in {elapsed:.2f}s")


async def download_object(object_storage: S3ObjectStorage, object_id: str):
    """TODO"""
    input_path = DATA_DIR / object_id
    file_size = input_path.stat().st_size
    download_url = await object_storage.get_object_download_url(
        bucket_id=BUCKET_ID, object_id=object_id
    )
    file_parts = download_file_parts(
        download_url=download_url, part_size=PART_SIZE, total_file_size=file_size
    )

    output_path = input_path.name.replace(".fasta", "_dl.fasta")
    with open(
        output_path,
        "wb",
        buffering=PART_SIZE,
    ) as target:
        # normally you'd use a for loop with enumerate, but we'd like to time
        # the actual download function which is wrapped by the generator
        duration = 0.0
        part_number = 0
        while True:
            part_number += 1
            download_start = time.time()
            try:
                file_part = next(file_parts)
            except StopIteration:
                break
            target.write(file_part)
            duration = duration + time.time() - download_start
            average = (PART_SIZE / 1024**2) / (duration / part_number)
            print(
                f"\rAverage transfer rate: {average:.2f} MiB/s (Part number {part_number})",
                end="",
            )
    print("\nRunning cleanup ...")
    await object_storage.delete_object(bucket_id=BUCKET_ID, object_id=object_id)
    if not filecmp.cmp(input_path, output_path):
        print(f"Input and output different for {input_path}", file=sys.stderr)
    os.remove(output_path)


if __name__ == "__main__":
    # assume localstack should be fairly reliable
    asyncio.run(benchmark_localstack())
    cos = DATA_DIR / "s3_cos.env"
    ceph = DATA_DIR / "s3_ceph.env"
    if cos.exists():
        config = S3ConfigBase(cos)
        asyncio.run(benchmark_remote(config=config))
    if ceph.exists():
        config = S3ConfigBase(ceph)
        asyncio.run(benchmark_remote(config=config))
