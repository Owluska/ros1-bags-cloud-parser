# Cloud ROSBag Parser

This script parses ROS1 `.bag` files stored in cloud storage accessible via `rclone`, extracts selected data from configured ROS topics, and saves the resulting dataset as a CSV file.

The parser is designed for batch processing large collections of bags from S3-like storage.

---

## Features

### Cloud bag discovery

- Lists available `.bag` files from a remote `rclone` path.
- Supports cloud paths such as:

```bash
S3:/levy-storage/queue/erg/
````

* Uses `rclone ls` to obtain:

  * relative bag path;
  * bag size in bytes.

---

### Bag size tracking

* Adds bag size to the output dataset.
* The size is stored in the column:

```text
bag_size_mb
```

* Size is calculated as:

```text
size_bytes / 1024 / 1024
```

---

### Duplicate protection

* Each cloud bag is processed only once.
* Duplicate bag paths are removed after cloud listing.
* Duplicate matches from `--list_file` are removed.
* Multiprocessing workers also skip already processed bags inside their own chunk.

Important: the script does **not** remove multiple output rows from the same bag, because one bag can produce multiple valid events or samples.

---

### Filtering support

The script supports filtering bags by:

#### Filename substring

```bash
--filter "121_2025-04-24"
```

#### List file

```bash
--list_file bags.txt
```

The list file may contain full bag names or substrings.

Example:

```text
121_2025-04-24
108_2026-01-10
```

Empty lines are ignored.

#### Date range

```bash
--date_0 2025-12-29-00-00-00
--date_1 2026-01-16-00-00-00
```

Date filtering is inclusive:

```text
date_0 <= bag_date <= date_1
```

The date is extracted from the bag name using the pattern:

```text
YYYY-MM-DD-HH-MM-SS
```

#### Vehicle ID

```bash
--vehid 108
```

The vehicle ID is taken from the first three characters of the bag basename.

Example:

```text
108_2026-01-10-12-00-00.bag
```

---

### Multiprocessing

* Supports parallel processing with multiple CPU workers.
* Number of processes is controlled by:

```bash
--n_cpu 12
```

* The bag list is split between workers.
* If there are fewer bags than requested workers, the number of workers is reduced automatically.

---

### Safe temporary files

* Each worker uses its own temporary directory.
* This avoids collisions when different workers copy bags with the same basename.
* Temporary files are deleted after processing.

---

### Checked cloud copying

* Bags are copied from cloud storage using:

```bash
rclone copy
```

* The script checks whether the copy command succeeded.
* If copying fails, the bag is skipped and the error is printed.
* If the expected local bag file is missing after copy, the bag is skipped.

---

### Configurable parser logic

The script uses an external parser configuration module:

```python
import parsers.throttle_const as p
```

This module should provide:

```python
p.topics
p.columns
```

Expected structure:

```python
topics = {
    "/topic/name": {
        "parser": parser_function,
        "type": "main"  # or auxiliary type
    }
}
```

The parser function receives:

```python
parser_function(msg, row, **kwargs)
```

and should return either:

```python
row
```

or:

```python
None
```

Rows are added to the dataset only when the topic type is:

```text
main
```

---

### Stateful topic parsing

The script intentionally keeps one shared `row` object while reading messages from a bag.

This allows auxiliary topics to update the current parser state, while main topics produce dataset rows.

Example:

```text
/speed_topic      -> updates speed
/state_topic      -> updates vehicle state
/main_event_topic -> saves current row
```

This means values from previous messages may be reused until updated by newer messages.

---

### CSV output

The resulting dataset is saved as CSV.

Default output:

```bash
df.csv
```

Custom output:

```bash
--output_path data.csv
```

Columns include:

```text
bag_name
bag_size_mb
time
date
vehid
```

plus custom columns from the selected parser module.

Iterable columns such as arrays/lists are automatically removed before saving to CSV.

---

## Usage

Example:

```bash
python3 cloud_bag_parser.py \
    --cloud_path S3:/levy-storage/queue/erg/ \
    --date_0 2025-12-29-00-00-00 \
    --date_1 2026-01-16-00-00-00 \
    --vehid 108 \
    --n_cpu 12 \
    --output_path data.csv
```

Example with filename filter:

```bash
python3 cloud_bag_parser.py \
    --cloud_path S3:/levy-storage/queue/suek \
    --filter "121_2025-04-24" \
    --output_path data.csv
```

Example with bag list:

```bash
python3 cloud_bag_parser.py \
    --cloud_path S3:/levy-storage/queue/erg/ \
    --list_file bags.txt \
    --n_cpu 8 \
    --output_path data.csv
```

Example with amount limit:

```bash
python3 cloud_bag_parser.py \
    --cloud_path S3:/levy-storage/queue/erg/ \
    --amount_limit 100 \
    --n_cpu 8 \
    --output_path data.csv
```

When `--amount_limit` is used, the bag list is shuffled first.

---

## Arguments

| Argument         | Required | Description                       |
| ---------------- | -------: | --------------------------------- |
| `--cloud_path`   |      yes | Root rclone path with ROS bags    |
| `--filter`       |       no | Substring filter for bag paths    |
| `--list_file`    |       no | File with bag names or substrings |
| `--date_0`       |       no | Inclusive lower date bound        |
| `--date_1`       |       no | Inclusive upper date bound        |
| `--vehid`        |       no | Vehicle ID filter                 |
| `--output_path`  |       no | Output CSV path                   |
| `--n_cpu`        |       no | Number of worker processes        |
| `--amount_limit` |       no | Maximum number of bags to process |

---

## Requirements

Python packages:

```bash
pip install pandas numpy tqdm pytz
```

ROS dependency:

```bash
rosbag
```

System dependency:

```bash
rclone
```

The cloud remote should be configured in `rclone` before running the script.

Check access with:

```bash
rclone ls S3:/levy-storage/queue/erg/
```

---

## Notes

### Date format

Bag names must contain a timestamp in this format:

```text
YYYY-MM-DD-HH-MM-SS
```

Example:

```text
108_2026-01-10-12-30-00.bag
```

If a bag does not contain exactly one timestamp matching this format, it is ignored when date filtering is used.

---

### One bag can produce multiple rows

The script guarantees that each bag file is copied and parsed once.

However, the output CSV may contain multiple rows with the same `bag_name`.

This is expected if the configured parser extracts multiple events or samples from one bag.

---

### Temporary files

Downloaded bags are stored temporarily under:

```text
./tmp/
```

Each worker creates its own temporary subdirectory.

Temporary files are deleted automatically after processing.
