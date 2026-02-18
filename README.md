# Sealback

This is a ~~simple~~ backup tool written in Python, using `tar` for archiving, `zstandard` for compression, and optionally `rclone` to upload backups to a
cloud provider.

`rclone` must be installed and configured separately in order to be used.
More information is available on the [rclone official website](https://rclone.org/).

---

## Features

- Backups using `tar`
- Compression using the Zstandard algorithm via the   [python-zstandard library](https://python-zstandard.readthedocs.io/en/stable/)
- Command Line Interface (CLI) built with   [Click](https://click.palletsprojects.com/en/stable/)
- Optional upload to cloud storage using `rclone`
- Load configuration from a JSON file
- checks integrity and security using `cryptography`

---

## Requirements

This project depends on the following external libraries:

- `zstandard`
- `click`

### Virtual environment setup

It is recommended to run this project inside a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Safety Notes

At this point this is an unfinished tool, still in development and shouldn't be used as a safe tool for backups.
But if you still consider using it, it's recommendable to test restoring any backups before relying on it.
Always avoid running this tool as root, unless you know what you're doing.

## CLI (Command Line Interface)

This tool provides a CLI for creating and restoring backups.
`create`:

```md
Usage: python -m src.cli create [OPTIONS] [SOURCES]...

Options:
  -o, --output PATH
  -l, --level INTEGER RANGE  Level to be used for the zstd algorithm
                             [default: (3); 0<=x<=22]
  --rclone TEXT              Rclone destination (ex: remote:backups)
  --force                    Overwrite output file if it already exists
  --file PATH                Load configuration from a JSON file
  --password TEXT            For encryption and integrity
  --help                     Show this message and exit.
```

`restore`:

```md
Usage: python -m src.cli restore [OPTIONS] [BACKUP]

Options:
  -o, --output PATH
  -f, --force        Overwrite files in destination if they exist
  --file PATH        Load configuration from a JSON file
  --password TEXT    For decryption and integrity check
  --help             Show this message and exit.
```

### JSON Config File

As of now, version 1 of the configuration file structure is used:

`example-config-file.json`:

```json
{
    "version": 1,
    "create": {
        "sources": [
            "/home/user/projects-example"
        ],
        "ouput": "/home/user/backups/projects-example-backup.seal",
        "level": 5,
        "rclone": "gdrive:backups"
    },
    "restore": {
        "backup": "/home/user/backups/projects-example-backup.seal",
        "output": "/home/user/restore",
        "checksum": true
    }
}
```

Using the config file:

```bash
python -m src.cli create --file ./example-config-file.json
```

in this case, this is the same as:

```bash
python -m src.cli create /home/user/projects-example \
  -o /home/user/backups/projects-example-backup.seal \
  -l 5 --rclone gdrive:backups
```

and

```bash
python -m src.cli restore --file ./example-config-file.json
```

is the same as:

```bash
python -m src.cli restore /home/user/backups/projects-example-backup.seal \
  -o /home/user/restore
```

### Notes

When creating a backup:

- At least one source path must be provided.
- When `--rclone` is provided, the backup file is uploaded using the `rclone` CLI.
- If the output path does not include a file extension `.tar.zst` will be appended automatically.

In both cases:

- If the output file already exists and `--force` is not specified, the command will exit with an error.
- When using a config file (with `--file`), values explicitly passed via cli will override values defined in the JSON file. So if a json file has `"level": 5` but `-l 20` is passed to the cli, the algorithm will use a level 20

### Examples

Create a backup of `/home/user/projects` and store it in `/home/user/backups`:

```bash
python -m src.cli create /home/user/projects \
  -o /home/user/backups/projects-backup.seal
```

Create a backup and upload it to a cloud remote:

```bash
python -m src.cli create /home/user/projects \
  -o /home/user/backups/projects-backup \
  --rclone gdrive:backups
```

Create a backup using a JSON file:

```bash
python -m src.cli create --file /home/user/projects/backup-projects-config.json
```
