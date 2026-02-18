from pathlib import Path
from datetime import datetime
import tempfile
import click
import shutil

from src.backup import create_tar
from src.compress import compress_zstd
# from src.checksum import sha256
from src.upload import upload_rclone

from src.decompress import decompress_zstd
from src.extract import safe_extract_tar, UnsafePathError
from src.verify import verify_sha256

from src.config import load_config, ConfigError

from src.crypto.format import write_enc_file, read_enc_file, DecryptionError

from src.manifest import (
    create_manifest,
    write_manifest,
    read_manifest_from_tar,
    validate_manifest,
    ManifestError,
    UnsupportedManifestVersion
)

def resolve_output_path(output: Path, zsuffix: str) -> Path:
    """ 
        Resolve the final output path for the backup archive
        
        Behavior:
        - If output is an existing directory, genereate a timestamp filename.
        - If output ends with the expected suffix, use it as-is.
        - If output is a filename without suffix, append the suffix.
    """
    if output.exists() and output.is_dir():
            base = f"backup-{datetime.now():%Y%m%d_%H%M%S}"
            return output / f"{base}{zsuffix}"

    if output.name.endswith(zsuffix):
        return output

    if output.parent.exists():
        return output.with_name(output.name + zsuffix)
    
    raise click.UsageError(f"Invalid output path: {output}")

@click.group()
@click.version_option()
def cli():
    """ Simple backup tool with zstd compression """
    pass
    
@cli.command()
@click.argument(
    "sources",
    type=click.Path(exists=True, path_type=Path),
    nargs=-1
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default="."
)
@click.option(
    "--level",
    "-l",
    type=click.IntRange(0, 22),
    help="Level to be used for the zstd algorithm",
    show_default="3"
)
@click.option(
    "--rclone",
    help="Rclone destination (ex: remote:backups)"
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite output file if it already exists"
)
@click.option(
    "--file",
    "config_file",
    type=click.Path(exists=True, path_type=Path),
    help="Load configuration from a JSON file"
)
@click.password_option(
    "--password",
    help="For encryption and integrity",
)
def create(sources, output, level, rclone, force, config_file, password):
    if not password:
        raise click.UsageError("Password cannot be empty")
    
    config = {}
    if config_file:
        try:
            config = load_config(config_file).get("create", {})
        except ConfigError as e:
            raise click.ClickException(str(e))

    # When --file is provided, options passed via cli
    # will override
    if not sources:
        sources = tuple(Path(p) for p in config.get("sources", []))

    output = output if output != Path(".") else Path(
        config.get("output", ".")
    )
    
    level = level if level is not None else config.get("level", 3)
    
    rclone = rclone if rclone is not None else config.get("rclone")
    
    if not sources:
        raise click.UsageError("No source provided")

    zsuffix = ".seal"
    
    final_path = resolve_output_path(output, zsuffix)
    if final_path.exists():
        if not force:
            raise click.UsageError(f"Output file already exists: {final_path}. (use --force to overwrite)")
        final_path.unlink()
    else:
        final_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo(f"Adding {len(sources)} source(s) to the backup file...")
    click.echo(f"Creating manifest...")
    manifest = create_manifest(
        list(sources),
        "zstd",
        level,
        "sealback",
        click.get_current_context().command_path
    )
    temp_dir = Path(tempfile.mkdtemp())
    manifest_path = write_manifest(manifest, temp_dir)

    try:
        tar_path = create_tar(list(sources), [manifest_path])
        click.echo("Compressing...")
        zst_path = compress_zstd(tar_path, level)
    except Exception:
        raise
    finally:
        if tar_path and tar_path.exists():
            tar_path.unlink()

        if manifest_path.exists():
            manifest_path.unlink()

        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    click.echo("Encrypting file...")
    try:
        encrypted_file = write_enc_file(
            zst_path,
            final_path,
            password,
        )
    except Exception:
        raise
    
    # shutil.move(zst_path, final_path)
    
    # click.echo("Generating checksum...")
    # sha256(final_path)

    if rclone:
        click.echo(f"Uploading to {rclone}")
        upload_rclone(encrypted_file, rclone)
        
@cli.command()
@click.argument(
    "backup",
    required=False,
    type=click.Path(exists=True, path_type=Path)
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default="."
)
# @click.option(
#     "--no-checksum",
#     is_flag=True,
#     help="Skip checksum verification"
# )
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Overwrite files in destination if they exist"
)
@click.option(
    "--file",
    "config_file",
    type=click.Path(exists=True, path_type=Path),
    help="Load configuration from a JSON file"
)
@click.password_option(
    "--password",
    help="For decryption and integrity check"
)
def restore(backup, output, force, config_file, password):
    config = {}
    if config_file:
        try:
            config = load_config(config_file).get("restore", {})
        except ConfigError as e:
            raise click.ClickException(str(e))
        
    # With --file provided, cli options will override it
    if backup is None:
        try:
            backup_value = Path(config.get("backup"))
        except TypeError:
            raise click.UsageError("No backup file provided (CLI or config file)")

        backup = Path(backup_value)
    
    output = output if output != Path(".") else Path(config.get("output", "."))
    
    # if not no_checksum:
        # no_checksum = not config.get("checksum", True)
    
    if backup.suffix != ".seal":
        raise click.UsageError("Backup must be a .seal file")
    
    output.mkdir(parents=True, exist_ok=True)
    
    # Checksum is verified before decompression to avoid
    # unecessary load, but there is a check agains manifest
    # later on, for now, just a redundancy
    # if not no_checksum:
    #     click.echo("Verifying checksum...")
    #     if not verify_sha256(backup):
    #         raise click.ClickException("Checksum verification failed")

    # header = create_header()

    try:
        click.echo("Decrypting file...")
        temp_dir = Path(tempfile.mkdtemp())
        decrypted_path = read_enc_file(
            backup,
            temp_dir,
            password
        )
    except:
        raise
    
    click.echo("Decompressing backup...")
    # decrypted_path = None
    tar_path = None
    try:
        tar_path = decompress_zstd(decrypted_path)
        
        click.echo("Reading manifest...")
        manifest = read_manifest_from_tar(tar_path)
        validate_manifest(manifest)
        
        # checksum_info = manifest.get("checksum", {})
        # algorithm = checksum_info.get("algorithm")
        
        # if no_checksum:
        #     click.echo("Checksum verification skipped by user")
        # else:
        #     if algorithm != "sha256":
        #         raise click.ClickException(f"Unsupported checksum algorithm: {algorithm}")
        
        sources = manifest.get("sources", [])
        if sources:
            click.echo("Backup contents:")
            for src in sources:
                click.echo(f" - {src['path']} ({src['type']})")

        click.echo("Extracting files...")
        if not force and any(output.iterdir()):
            raise click.UsageError(f"Output directory is not empty {output} (use --force)")
        
        safe_extract_tar(tar_path, output, force=force)

    except UnsupportedManifestVersion as e:
        raise click.ClickException(str(e))
    except ManifestError as e:
        raise click.ClickException(f"Invalid backup manifest: {e}")
    except UnsafePathError as e:
        raise click.ClickException(f"Error: {e}")

    finally:
        if tar_path and tar_path.exists():
            tar_path.unlink()
            
    click.echo("Restore completed succesfully")
        
if __name__ == "__main__":
    cli()
