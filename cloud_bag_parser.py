import os
import subprocess
import pytz
import rosbag
import traceback
import tqdm
import re
import numpy as np
import random
import argparse
import pandas as pd
import tempfile

from datetime import datetime
from multiprocessing import Pool


def topic_parser(func):
    def inner(message, row, **kwargs):
        result = func(message, row, **kwargs)
        return result

    return inner


def is_iterable(obj):
    return hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes))


class Parser:
    tz = 'Asia/Oral'
    tmp_dir = 'tmp'

    def __init__(
        self,
        cloud_path,
        bags_list,
        cloud_filter,
        date_0,
        date_1,
        vehid,
        topics_n_parsers,
        columns,
        amount_limit=None,
    ):
        self.df = []

        self.cloud_path = cloud_path
        self.bags_list = bags_list
        self.cloud_filter = cloud_filter
        self.date_0 = date_0
        self.date_1 = date_1
        self.vehid = str(vehid) if vehid is not None else None

        self.columns = ['bag_name', 'bag_size_mb', 'time', 'date', 'vehid'] + columns
        self.bag_sizes_mb = {}

        self.amount_limit = amount_limit

        self.topics_n_parsers = topics_n_parsers
        self.topics = list(self.topics_n_parsers.keys())

        root = os.getcwd()
        self.tmp_dir = os.path.join(root, self.tmp_dir)

        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir, mode=0o777)

    def bag_name_to_date(self, bag_name):
        bag_name = bag_name.replace("/", "")
        pattern = r'\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}'
        matches = re.findall(pattern, bag_name)

        if matches is None or len(matches) != 1:
            return None

        return matches[0]

    def is_bag_after_or_equal(self, bag_name, date_s):
        bag_date = self.bag_name_to_date(bag_name)
        return bag_date is not None and bag_date >= date_s

    def is_bag_before_or_equal(self, bag_name, date_s):
        bag_date = self.bag_name_to_date(bag_name)
        return bag_date is not None and bag_date <= date_s

    def get_vehid_bags(self, bag_names):
        return [
            f for f in bag_names
            if f.endswith('.bag') and os.path.basename(f)[:3] == self.vehid
        ]

    def rclone_join(self, root, relative_path):
        return root.rstrip("/") + "/" + relative_path.lstrip("/")

    def parse_rclone_ls_output(self, output):
        """
        rclone ls output format:
            <size_bytes> <relative_path>

        Example:
            123456789 folder/subfolder/121_2025-04-24-10-00-00.bag
        """
        file_items = []

        for line in output.splitlines():
            line = line.strip()

            if not line:
                continue

            parts = line.split(maxsplit=1)

            if len(parts) != 2:
                continue

            size_bytes_str, file_name = parts

            try:
                size_bytes = int(size_bytes_str)
            except ValueError:
                continue

            size_mb = size_bytes / (1024 * 1024)
            file_items.append((file_name, size_mb))

        return file_items

    def get_list_of_cloud_files(self):
        cmd = ["rclone", "ls", self.cloud_path]

        print("Requesting bag's list from cloud, cmd: {}".format(" ".join(cmd)))

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode != 0:
            print("Failed to request cloud file list")
            print(result.stderr)
            return []

        if result.stderr.strip():
            print("rclone stderr:", result.stderr.strip())

        file_items = self.parse_rclone_ls_output(result.stdout)

        # Keep only bags.
        file_items = [
            (name, size_mb)
            for name, size_mb in file_items
            if name.endswith(".bag")
        ]

        # Apply cloud filter in Python instead of shell grep.
        if self.cloud_filter:
            file_items = [
                (name, size_mb)
                for name, size_mb in file_items
                if self.cloud_filter in name
            ]

        # Filter by list_file patterns.
        if self.bags_list is not None:
            clean_patterns = [
                pattern.strip()
                for pattern in self.bags_list
                if pattern.strip()
            ]

            file_items = [
                (name, size_mb)
                for name, size_mb in file_items
                if any(pattern in name for pattern in clean_patterns)
            ]

        # Deduplicate by cloud-relative path, preserving first occurrence.
        unique_file_items = {}

        for name, size_mb in file_items:
            if name not in unique_file_items:
                unique_file_items[name] = size_mb

        file_items = list(unique_file_items.items())

        # Save size map before further filtering.
        self.bag_sizes_mb = {
            name: size_mb
            for name, size_mb in file_items
        }

        file_names = [name for name, _ in file_items]

        # Date-based filters.
        # These are inclusive:
        #   date_0 <= bag_date <= date_1
        if self.date_0 or self.date_1:
            file_names = [
                f for f in file_names
                if self.bag_name_to_date(f) is not None
            ]

        if self.date_0:
            file_names = [
                f for f in file_names
                if self.is_bag_after_or_equal(f, self.date_0)
            ]

        if self.date_1:
            file_names = [
                f for f in file_names
                if self.is_bag_before_or_equal(f, self.date_1)
            ]

        if self.vehid:
            file_names = self.get_vehid_bags(file_names)

        # Sort by name, so different vehicles will not be mixed.
        file_names = sorted(file_names)

        # Final deduplication, preserving order.
        file_names = list(dict.fromkeys(file_names))

        return file_names

    def parser(self, bag_object, bag_name, bag_size_mb=None, **kwargs):
        row = {col: None for col in self.columns}

        row['bag_name'] = bag_name
        row['bag_size_mb'] = bag_size_mb
        row['vehid'] = bag_name[:3]

        data = []

        for topic, msg, time in bag_object.read_messages(topics=self.topics):
            row['time'] = time.to_sec()
            row['date'] = datetime.fromtimestamp(
                time.to_sec(),
                tz=pytz.timezone(self.tz),
            )

            result = self.topics_n_parsers[topic]['parser'](
                msg,
                row,
                **kwargs,
            )

            if result is None:
                continue

            row = result

            if self.topics_n_parsers[topic]['type'] == 'main':
                data.append(row.copy())

        return data

    def split_bags(self, bags_names, n):
        if not bags_names:
            return []

        n = max(1, min(n, len(bags_names)))

        chunks = []

        for i in range(n):
            start = int(len(bags_names) * i / n)
            end = int(len(bags_names) * (i + 1) / n)

            chunk = bags_names[start:end]

            if chunk:
                chunks.append(chunk)

        return chunks

    def launch(self, n, **kwargs):
        bags_names = self.get_list_of_cloud_files()

        if not bags_names:
            print("No bags found")
            return

        print("Found {} unique bags".format(len(bags_names)))

        if self.amount_limit is not None:
            random.shuffle(bags_names)
            bags_names = bags_names[:self.amount_limit]
            print("Limited to {} bags".format(len(bags_names)))

        bags_splited = self.split_bags(bags_names, n)

        if not bags_splited:
            print("No bags to process after splitting")
            return

        n_workers = len(bags_splited)

        print("Processing with {} worker(s)".format(n_workers))

        with Pool(processes=n_workers) as pool:
            multiple_results = [
                pool.apply_async(
                    self.work,
                    args=(files,),
                    kwds=kwargs,
                )
                for files in bags_splited
            ]

            for res in multiple_results:
                self.df.extend(res.get())

    def work(self, bags_names, **kwargs):
        data = []
        processed_bags = set()

        with tempfile.TemporaryDirectory(dir=self.tmp_dir) as worker_tmp_dir:
            pbar = tqdm.tqdm(bags_names)

            for cloud_bag_path in pbar:
                if cloud_bag_path in processed_bags:
                    continue

                processed_bags.add(cloud_bag_path)

                _, name = os.path.split(cloud_bag_path)

                bag_size_mb = self.bag_sizes_mb.get(cloud_bag_path)

                full_cloud_bag_path = self.rclone_join(
                    self.cloud_path,
                    cloud_bag_path,
                )

                pbar.set_description(name[:-4])
                pbar.set_postfix_str('copying')

                copy_cmd = [
                    "rclone",
                    "copy",
                    full_cloud_bag_path,
                    worker_tmp_dir,
                ]

                copy_result = subprocess.run(
                    copy_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                if copy_result.returncode != 0:
                    pbar.set_postfix_str('copy failed')
                    print("Failed to copy: {}".format(full_cloud_bag_path))
                    print(copy_result.stderr)
                    continue

                bag_path = os.path.join(worker_tmp_dir, name)

                if not os.path.exists(bag_path):
                    pbar.set_postfix_str('bag not found after copy')
                    print("Bag was not found after copy: {}".format(bag_path))
                    continue

                try:
                    pbar.set_postfix_str('parsing')

                    with rosbag.Bag(
                        bag_path,
                        'r',
                        allow_unindexed=True,
                    ) as bag:
                        data_cur = self.parser(
                            bag,
                            name,
                            bag_size_mb=bag_size_mb,
                            **kwargs,
                        )

                        if len(data_cur):
                            data.extend(data_cur)

                except Exception as e:
                    pbar.set_postfix_str(
                        'Error processing: {}'.format(str(e))
                    )
                    traceback.print_exc()

                finally:
                    if os.path.exists(bag_path):
                        pbar.set_postfix_str('removing')

                        try:
                            os.remove(bag_path)
                        except OSError:
                            traceback.print_exc()

        return data

    def save_dataframe(self, output_path=None):
        print("Rows collected:", len(self.df))

        self.df = pd.DataFrame(self.df)

        if len(self.df) == 0:
            print("No data to save")
            return

        array_cols = [
            col for col in self.df.columns
            if np.any(self.df[col].apply(lambda x: is_iterable(x)))
        ]

        if not output_path:
            output_path = os.path.join(os.getcwd(), 'df.csv')

        print('Saving to {}'.format(output_path))

        self.df.drop(columns=array_cols).to_csv(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse ROSBags')

    parser.add_argument(
        '--cloud_path',
        help='Root path of ROSBags',
        required=True,
    )

    parser.add_argument(
        '--filter',
        help='Filter for search bags',
        required=False,
        default=None,
    )

    parser.add_argument(
        '--list_file',
        help='File with list of bag names or name substrings',
        required=False,
        default=None,
    )

    parser.add_argument(
        '--date_0',
        help='Date after - inclusive lower bound: %Y-%m-%d-%H-%M-%S',
        required=False,
        default=None,
    )

    parser.add_argument(
        '--date_1',
        help='Date before - inclusive upper bound: %Y-%m-%d-%H-%M-%S',
        required=False,
        default=None,
    )

    parser.add_argument(
        '--vehid',
        help='Vehid - filter by vehid',
        required=False,
        default=None,
    )

    parser.add_argument(
        '--output_path',
        help='Output path for csv file',
        required=False,
        default=None,
    )

    parser.add_argument(
        '--n_cpu',
        help='Number of processes',
        required=False,
        default=8,
        type=int,
    )

    parser.add_argument(
        '--amount_limit',
        help='Limit for the max bags amount',
        required=False,
        default=None,
        type=int,
    )

    args = parser.parse_args()

    output_path = args.output_path
    list_file = args.list_file
    bags_list = None

    if list_file is not None:
        with open(list_file, 'r') as lf:
            bags_list = [
                line.strip()
                for line in lf.readlines()
                if line.strip()
            ]

    import parsers.throttle_const as p
    kwargs = p.kwargs
    p = Parser(
        cloud_path=args.cloud_path,
        bags_list=bags_list,
        cloud_filter=args.filter,
        date_0=args.date_0,
        date_1=args.date_1,
        vehid=args.vehid,
        topics_n_parsers=p.topics,
        columns=p.columns,
        amount_limit=args.amount_limit,
    )



    p.launch(int(args.n_cpu), **kwargs)
    p.save_dataframe(output_path)

    print(p.df.info())