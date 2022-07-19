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
import asyncio
import os
import time
from pathlib import Path

from ghga_connector.core.file_operations import (  # type: ignore
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
FILE_PATHS = [
    DATA_DIR / file_name
    for file_name in os.listdir(DATA_DIR)
    if not file_name.endswith(".md")
]
OBJECT_IDS: list[str] = []
PART_SIZE = 16 * 1024 * 1024


async def benchmark_localstack():
    """TODO"""
    with LocalStackContainer(image="localstack/localstack:0.14.2").with_services(
        "s3"
    ) as localstack:
        config = config_from_localstack_container(localstack)
        storage = S3ObjectStorage(config=config)
        await storage.create_bucket(BUCKET_ID)
        await benchmark_upload(object_storage=storage)


def benchmark_remote(config: S3ConfigBase):
    """TODO: Get config to inject from env variables"""
    object_storage = S3ObjectStorage(config=config)
    benchmark_upload(object_storage=object_storage)


async def benchmark_upload(object_storage: S3ObjectStorage):
    """TODO"""
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

    durations = []
    with open(path, "r+b") as source:
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
            durations.append(time.time() - upload_start)
            average = (PART_SIZE / 1024**2) / (sum(durations) / len(durations))
            print(
                f"\rAverage transfer rate: {average:.2f} MiB/s (Part number {part_number})",
                end="",
            )
    print()
    await object_storage.complete_multipart_upload(
        upload_id=upload_id, bucket_id=BUCKET_ID, object_id=object_id
    )


def benchmark_download(object_storage: S3ObjectStorage):
    """TODO"""
    for object_id in OBJECT_IDS:
        print(f"Downloading object {object_id}")
        upload_start = time.time()
        asyncio.run(download_object(object_storage=object_storage, object_id=object_id))
        elapsed = time.time() - upload_start
        print(f"Download for object {object_id} finished in {elapsed:.2f}s")


async def download_object(
    object_storage: S3ObjectStorage, object_id: str
):  # pylint: disable=unused-argument
    """TODO"""
    durations = []
    download_start = time.time()
    # Place function call here
    durations.append(time.time() - download_start)
    average = (PART_SIZE / 1024**2) / (sum(durations) / len(durations))
    print(f"Average transfer rate: {average:.2f} MiB/s", end="")


if __name__ == "__main__":
    WithRetry.set_retries(0)
    asyncio.run(benchmark_localstack())
