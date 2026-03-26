import gradio as gr
from pathlib import Path
from .analyzer import analyze_image, rename_photo
import json
import os

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def process_photo(image_path: str, include_people: bool, apply_rename: bool):
    """Process a single photo and return results."""
    if image_path is None:
        return "Please upload a photo first.", "", "", "", ""

    try:
        result = analyze_image(image_path, include_people=include_people)

        new_filename = f"{result['filename_with_date']}{result['extension']}"
        people = result.get("people", [])
        people_str = (
            ", ".join(people)
            if people and people != ["no-people"]
            else "No people detected"
        )
        tags_str = ", ".join(result.get("tags", []))

        rename_status = ""
        if apply_rename:
            new_path = rename_photo(image_path, result, dry_run=False)
            rename_status = f"✅ Renamed to: {new_path}"
        else:
            rename_status = (
                f"💡 Suggested: {new_filename} (enable 'Apply Rename' to rename)"
            )

        return new_filename, result["description"], tags_str, people_str, rename_status

    except Exception as e:
        return "", "", "", "", f"❌ Error: {str(e)}"


def process_batch(
    folder_path: str, include_people: bool, apply_rename: bool, progress=gr.Progress()
):
    """Process all photos in a folder."""
    if not folder_path or not folder_path.strip():
        return "❌ Please enter a folder path.", ""

    folder = Path(folder_path).expanduser()
    if not folder.exists():
        return f"❌ Folder not found: {folder_path}", ""

    photos = [f for f in folder.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not photos:
        return f"❌ No supported photos found in {folder_path}", ""

    results = []
    errors = []
    log_lines = [f"📁 Found {len(photos)} photos in {folder_path}\n"]

    for i, photo in enumerate(progress.tqdm(photos, desc="Analyzing photos")):
        log_lines.append(f"[{i+1}/{len(photos)}] Analyzing: {photo.name}")
        try:
            result = analyze_image(str(photo), include_people=include_people)
            new_filename = f"{result['filename_with_date']}{result['extension']}"
            log_lines.append(f"  ✨ → {new_filename}")

            if apply_rename:
                rename_photo(str(photo), result, dry_run=False)
                log_lines.append(f"  ✅ Renamed!")

            results.append(
                {
                    "original": photo.name,
                    "suggested": new_filename,
                    "description": result["description"],
                    "tags": ", ".join(result.get("tags", [])),
                    "people": ", ".join(result.get("people", [])),
                }
            )
        except Exception as e:
            log_lines.append(f"  ❌ Error: {str(e)}")
            errors.append(photo.name)

    # Summary
    log_lines.append(f"\n✅ Done! {len(results)} succeeded, {len(errors)} failed.")
    if errors:
        log_lines.append(f"❌ Failed: {', '.join(errors)}")

    # Build results table
    table = "| Original | Suggested | Description |\n|---|---|---|\n"
    for r in results:
        table += (
            f"| {r['original']} | {r['suggested']} | {r['description'][:60]}... |\n"
        )

    return "\n".join(log_lines), table


def build_ui():
    with gr.Blocks(title="PhotoMind") as app:

        gr.Markdown(
            """
        # 📸 PhotoMind
        ### Give Meaningful Names to Your Photos with AI
        """
        )

        with gr.Tabs():

            # ── Tab 1: Single Photo ──────────────────────────────────────
            with gr.Tab("🖼️ Single Photo"):
                with gr.Row():
                    with gr.Column(scale=1):
                        image_input = gr.Image(
                            type="filepath", label="Upload Photo", height=300
                        )
                        with gr.Row():
                            include_people = gr.Checkbox(
                                label="Detect People", value=True
                            )
                            apply_rename = gr.Checkbox(
                                label="Apply Rename", value=False
                            )
                        analyze_btn = gr.Button(
                            "✨ Analyze Photo", variant="primary", size="lg"
                        )

                    with gr.Column(scale=1):
                        filename_output = gr.Textbox(
                            label="📁 Suggested Filename", interactive=False
                        )
                        description_output = gr.Textbox(
                            label="📝 Description", interactive=False, lines=3
                        )
                        tags_output = gr.Textbox(label="🏷️ Tags", interactive=False)
                        people_output = gr.Textbox(label="👤 People", interactive=False)
                        status_output = gr.Textbox(label="Status", interactive=False)

                analyze_btn.click(
                    fn=process_photo,
                    inputs=[image_input, include_people, apply_rename],
                    outputs=[
                        filename_output,
                        description_output,
                        tags_output,
                        people_output,
                        status_output,
                    ],
                )

            # ── Tab 2: Batch Folder ──────────────────────────────────────
            with gr.Tab("📁 Batch Folder"):
                with gr.Row():
                    with gr.Column(scale=1):
                        folder_input = gr.Textbox(
                            label="Folder Path",
                            placeholder="e.g. ~/Pictures/vacation or /Users/rish/Photos",
                        )
                        with gr.Row():
                            batch_people = gr.Checkbox(
                                label="Detect People", value=True
                            )
                            batch_rename = gr.Checkbox(
                                label="Apply Rename", value=False
                            )
                        batch_btn = gr.Button(
                            "🚀 Process Folder", variant="primary", size="lg"
                        )
                        gr.Markdown(
                            """
                        ⚠️ **Warning:** Enable 'Apply Rename' only when you're ready to rename files.
                        Always do a dry run first!
                        """
                        )

                    with gr.Column(scale=1):
                        batch_log = gr.Textbox(
                            label="📋 Progress Log", interactive=False, lines=15
                        )

                batch_results = gr.Markdown(label="Results")

                batch_btn.click(
                    fn=process_batch,
                    inputs=[folder_input, batch_people, batch_rename],
                    outputs=[batch_log, batch_results],
                )

        gr.Markdown(
            """
        ---
        💡 **Tips:**
        - **Single Photo** — drag & drop to preview suggested name before renaming
        - **Batch Folder** — process entire folders, always dry run first!
        - Supports JPG, PNG, GIF, WebP
        """
        )

    return app


if __name__ == "__main__":
    app = build_ui()
    app.launch()
