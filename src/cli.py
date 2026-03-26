import click
import os
import json
from pathlib import Path
from .analyzer import analyze_image, rename_photo

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@click.group()
def cli():
    """
    PhotoMInd - Give meaningful names to your photos with AI
    """
    pass


@cli.command()
@click.argument("image_path")
@click.option(
    "--rename", is_flag=True, help="Actually rename the file (default is dry run)"
)
@click.option("--no-people", is_flag=True, help="Skip people detection")
def analyze(image_path, rename, no_people):
    """Analyze a single photo and suggest a meaningful name."""
    if not os.path.exists(image_path):
        click.echo(f"❌ File not found: {image_path}")
        return

    click.echo(f"🔍 Analyzing: {image_path}")
    result = analyze_image(image_path, include_people=not no_people)

    click.echo(f"\n📸 Original:    {result['original_filename']}")
    click.echo(f"✨ Suggested:   {result['filename_with_date']}{result['extension']}")
    click.echo(f"📝 Description: {result['description']}")
    click.echo(f"🏷️  Tags:        {', '.join(result['tags'])}")

    if result.get("people") and result["people"] != ["no-people"]:
        click.echo(f"👤 People:      {', '.join(result['people'])}")

    if result.get("exif_date"):
        click.echo(f"📅 Date:        {result['exif_date']}")

    if rename:
        new_path = rename_photo(image_path, result, dry_run=False)
        click.echo(f"\n✅ Renamed to: {new_path}")
    else:
        new_path = rename_photo(image_path, result, dry_run=True)
        click.echo(f"\n💡 Run with --rename to apply. New path would be: {new_path}")


@cli.command()
@click.argument("folder_path")
@click.option(
    "--rename", is_flag=True, help="Actually rename files (default is dry run)"
)
@click.option("--no-people", is_flag=True, help="Skip people detection")
@click.option("--output-json", help="Save results to a JSON file")
def batch(folder_path, rename, no_people, output_json):
    """Batch analyze all photos in a folder."""
    folder = Path(folder_path)
    if not folder.exists():
        click.echo(f"❌ Folder not found: {folder_path}")
        return

    photos = [f for f in folder.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not photos:
        click.echo(f"❌ No supported photos found in {folder_path}")
        return

    click.echo(f"📁 Found {len(photos)} photos in {folder_path}\n")

    results = []
    for i, photo in enumerate(photos, 1):
        click.echo(f"[{i}/{len(photos)}] Analyzing: {photo.name}")
        try:
            result = analyze_image(str(photo), include_people=not no_people)
            result["status"] = "success"

            click.echo(f"  ✨ → {result['filename_with_date']}{result['extension']}")

            if rename:
                rename_photo(str(photo), result, dry_run=False)
                click.echo(f"  ✅ Renamed!")

            results.append(result)
        except Exception as e:
            click.echo(f"  ❌ Error: {e}")
            results.append(
                {"original_filename": photo.name, "status": "error", "error": str(e)}
            )

    click.echo(f"\n✅ Done! Processed {len(results)} photos.")

    if output_json:
        with open(output_json, "w") as f:
            json.dump(results, f, indent=2)
        click.echo(f"📄 Results saved to {output_json}")
