import gradio as gr
from pathlib import Path
from .analyzer import analyze_image, rename_photo
from .enroll import enroll_from_folder, enroll_unknown_face, get_unknown_faces
from .database import list_known_people
import json
import os

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def process_photo(image_path, include_people, apply_rename, output_folder):
    """Process a single photo and return results."""
    if image_path is None:
        return "Please upload a photo first.", "", "", "", "", [], [], []

    try:
        # Check for unknown faces first
        unknown_faces = get_unknown_faces(image_path) if include_people else []

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
            # Save to output folder instead of renaming in place
            out_folder = Path(output_folder).expanduser()
            out_folder.mkdir(parents=True, exist_ok=True)
            new_path = out_folder / new_filename

            # Copy renamed file to output folder
            import shutil

            shutil.copy2(image_path, str(new_path))
            rename_status = f"✅ Saved to: {new_path}"
        else:
            rename_status = f"💡 Suggested: {new_filename}"

        # Prepare unknown faces
        unknown_crop_paths = [f["crop_path"] for f in unknown_faces]
        unknown_crops_gallery = [
            (path, f"Face {i}") for i, path in enumerate(unknown_crop_paths)
        ]
        unknown_encodings = [json.dumps(f["encoding"]) for f in unknown_faces]

        return (
            new_filename,
            result["description"],
            tags_str,
            people_str,
            rename_status,
            unknown_crops_gallery,
            unknown_encodings,
            unknown_crop_paths,
        )

    except Exception as e:
        return "", "", "", "", f"❌ Error: {str(e)}", [], [], []


def enroll_selected(name, index, encodings, crop_paths):
    """Enroll an unknown face with a user-provided name."""
    if not encodings:
        return "❌ No unknown faces detected in this photo!"
    if not name.strip():
        return "❌ Please enter a name!"
    idx = int(index)
    if idx >= len(encodings):
        return f"❌ Face #{idx} not found. Valid range: 0-{len(encodings)-1}"
    return enroll_face(name, encodings[idx], crop_paths[idx])


def enroll_face(name, encoding_json, crop_path):
    """Enroll an unknown face with a name."""
    try:
        encoding = json.loads(encoding_json)
        result = enroll_unknown_face(encoding, name.strip(), crop_path)
        return result["message"]
    except Exception as e:
        return f"❌ Error: {str(e)}"


def process_batch(folder_path, include_people, apply_rename, progress=gr.Progress()):
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

            if result.get("known_people"):
                log_lines.append(f"  👤 Known: {', '.join(result['known_people'])}")

            if apply_rename:
                rename_photo(str(photo), result, dry_run=False)
                log_lines.append(f"  ✅ Renamed!")

            results.append(
                {
                    "original": photo.name,
                    "suggested": new_filename,
                    "known_people": ", ".join(result.get("known_people", [])),
                }
            )
        except Exception as e:
            log_lines.append(f"  ❌ Error: {str(e)}")
            errors.append(photo.name)

    log_lines.append(f"\n✅ Done! {len(results)} succeeded, {len(errors)} failed.")

    table = "| Original | Suggested | Known People |\n|---|---|---|\n"
    for r in results:
        table += (
            f"| {r['original']} | {r['suggested']} | {r['known_people'] or 'none'} |\n"
        )

    return "\n".join(log_lines), table


def enroll_from_folder_ui(folder_path):
    """Enroll all people from a reference folder."""
    if not folder_path.strip():
        return "❌ Please enter a folder path."
    results = enroll_from_folder(folder_path)
    lines = [r["message"] for r in results]
    return "\n".join(lines)


def get_known():
    """Get list of known people."""
    people = list_known_people()
    return (
        "\n".join([f"• {p}" for p in people]) if people else "No people enrolled yet."
    )


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
                        output_folder = gr.Textbox(
                            label="📂 Output Folder",
                            placeholder="e.g. ~/renamed-photos",
                            value="~/renamed-photos",
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

                # Unknown faces section
                gr.Markdown("---\n### 🔍 Unknown Faces — Who is this?")

                unknown_encodings_state = gr.State([])
                unknown_crops_state = gr.State([])

                unknown_gallery = gr.Gallery(
                    label="Unknown faces — select face number below to enroll",
                    columns=4,
                    height=200,
                )

                with gr.Row():
                    unknown_name_input = gr.Textbox(
                        label="Name", placeholder="Enter person's name e.g. john"
                    )
                    unknown_index = gr.Number(
                        label="Face # (0 = first face)", value=0, precision=0
                    )
                    enroll_btn = gr.Button("➕ Enroll This Person", variant="secondary")

                enroll_status = gr.Textbox(label="Enrollment Status", interactive=False)

                analyze_btn.click(
                    fn=process_photo,
                    inputs=[image_input, include_people, apply_rename, output_folder],
                    outputs=[
                        filename_output,
                        description_output,
                        tags_output,
                        people_output,
                        status_output,
                        unknown_gallery,
                        unknown_encodings_state,
                        unknown_crops_state,
                    ],
                )

                enroll_btn.click(
                    fn=enroll_selected,
                    inputs=[
                        unknown_name_input,
                        unknown_index,
                        unknown_encodings_state,
                        unknown_crops_state,
                    ],
                    outputs=[enroll_status],
                )

            # ── Tab 2: Batch Folder ──────────────────────────────────────
            with gr.Tab("📁 Batch Folder"):
                with gr.Row():
                    with gr.Column(scale=1):
                        folder_input = gr.Textbox(
                            label="Folder Path", placeholder="e.g. ~/Pictures/vacation"
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
                        gr.Markdown("⚠️ Always dry run first before applying rename!")

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

            # ── Tab 3: Manage People ─────────────────────────────────────
            with gr.Tab("👥 Manage People"):
                gr.Markdown("### Enroll people from a reference folder")
                with gr.Row():
                    enroll_folder_input = gr.Textbox(
                        label="Reference Folder Path",
                        placeholder="e.g. ~/working/p2-projects/photomind/reference_faces",
                    )
                    enroll_folder_btn = gr.Button("📥 Enroll All", variant="primary")

                enroll_folder_status = gr.Textbox(
                    label="Status", interactive=False, lines=10
                )

                enroll_folder_btn.click(
                    fn=enroll_from_folder_ui,
                    inputs=[enroll_folder_input],
                    outputs=[enroll_folder_status],
                )

                gr.Markdown("### Known People in Database")
                refresh_btn = gr.Button("🔄 Refresh List")
                known_people_output = gr.Textbox(
                    label="Enrolled People", interactive=False, lines=5
                )

                refresh_btn.click(fn=get_known, outputs=[known_people_output])

        gr.Markdown(
            """
        ---
        💡 **Tips:**
        - **Single Photo** — upload photo, see unknown faces, enter name and click Enroll!
        - **Batch Folder** — always dry run first
        - **Manage People** — enroll from reference folder or view enrolled people
        """
        )

    return app


if __name__ == "__main__":
    app = build_ui()
    app.launch()
