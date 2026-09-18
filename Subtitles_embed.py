

#
# from flask import Flask, request, jsonify, send_file
# from flask_cors import CORS
# import whisper
# import subprocess
# import os
# import uuid
# import threading
# import time
# import re
# import glob
# import json
#
# app = Flask(__name__)
# CORS(app)
#
# UPLOAD_FOLDER = "uploads"
# CLIPS_FOLDER  = "uploads/clips"
# OUTPUT_FOLDER = r"D:\EMS"
# MODEL_PATH="Whisper-model/small.pt"
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# os.makedirs(CLIPS_FOLDER, exist_ok=True)
# os.makedirs(OUTPUT_FOLDER, exist_ok=True)
# TARGET_W, TARGET_H = 1080, 1920  # standard reel canvas — keeps sizing consistent across modes
#
# jobs = {}
#
# print("Loading Whisper model...")
# model = whisper.load_model(MODEL_PATH)
# print("Whisper ready!\n")
#
#
# # ─────────────────────────────────────────────────────────────
# # HELPERS (unchanged from your original)
# # ─────────────────────────────────────────────────────────────
# def hex_to_rgb(h):
#     h = h.lstrip("#")
#     return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
#
#
# def time_str_to_seconds(t):
#     parts = t.strip().split(":")
#     if len(parts) == 2:
#         return int(parts[0]) * 60 + float(parts[1])
#     elif len(parts) == 3:
#         return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
#     return float(t)
#
#
# def get_video_duration(video_path):
#     try:
#         r = subprocess.run([
#             "ffprobe", "-v", "error",
#             "-show_entries", "format=duration",
#             "-of", "default=noprint_wrappers=1:nokey=1",
#             video_path
#         ], capture_output=True, text=True, check=True)
#         return float(r.stdout.strip())
#     except:
#         return None
#
#
# def group_words(words, max_words=2):
#     chunks = []
#     i = 0
#     while i < len(words):
#         chunk = words[i: i + max_words]
#         start = chunk[0]["start"]
#         end   = chunk[-1]["end"]
#         text  = " ".join(w["word"].strip() for w in chunk)
#         chunks.append({"start": start, "end": end, "text": text})
#         i += max_words
#     return chunks
#
#
# def contains_arabic(text):
#     return bool(re.search(r'[\u0600-\u06FF\u0750-\u077F]', text))
#
# def cleanup_job_uploads(job_id):
#     """Deletes every temp/upload file this job used — never touches OUTPUT_FOLDER,
#     so the finished render is always safe."""
#     job = jobs.get(job_id, {})
#     paths_to_remove = list(job.get("source_paths", []))
#     if job.get("logo_path"):
#         paths_to_remove.append(job["logo_path"])
#     if job.get("music_path"):
#         paths_to_remove.append(job["music_path"])
#
#     for p in paths_to_remove:
#         try:
#             if p and os.path.exists(p):
#                 os.remove(p)
#         except Exception as e:
#             print(f"[CLEANUP] Could not remove {p}: {e}")
#
#     # everything else this job generated (crop/merge/audioswap/whisper-wav/box/wc pngs)
#     # was named with the job_id prefix inside UPLOAD_FOLDER
#     for f in glob.glob(os.path.join(UPLOAD_FOLDER, f"{job_id}*")):
#         try:
#             os.remove(f)
#         except Exception as e:
#             print(f"[CLEANUP] Could not remove {f}: {e}")
#
#     print(f"[CLEANUP] Job {job_id[:8]} uploads wiped (output preserved)")
#
#
# def shape_arabic_text(text):
#     """Reshapes Arabic text for correct glyph joining + RTL display order."""
#     try:
#         import arabic_reshaper
#         from bidi.algorithm import get_display
#         reshaped = arabic_reshaper.reshape(text)
#         return get_display(reshaped)
#     except ImportError:
#         print("[WARN] arabic_reshaper/python-bidi not installed — Arabic text may render disconnected")
#         return text
#
#
# # ─────────────────────────────────────────────────────────────
# # NEW: per-word color helpers (word-level subtitle emphasis)
# # ─────────────────────────────────────────────────────────────
# def parse_word_colors(raw_dict):
#     """
#     Converts a JSON-ish dict of {"0": "#ff0000", "3": "#00ff00"} (word index -> hex)
#     coming from the frontend into {0: (255,0,0), 3: (0,255,0)}.
#     Silently skips anything malformed instead of failing the whole render.
#     """
#     parsed = {}
#     if not raw_dict:
#         return parsed
#     for k, v in raw_dict.items():
#         try:
#             idx = int(k)
#             parsed[idx] = hex_to_rgb(v)
#         except (ValueError, TypeError):
#             continue
#     return parsed
#
#
# def build_multicolor_text_image(words, font_path, font_size, default_color,
#                                  style, stroke_width=5, stroke_color=(0, 0, 0),
#                                  max_width=900, crop_to_ink=True):
#     """
#     Renders a (possibly multi-line, word-wrapped) block of text where each word can
#     carry its own RGB color override. Returns (PIL.Image RGBA, (width, height)).
#
#     words: list of dicts -> {"text": str, "color": (r,g,b) or None}
#            color=None means "use default_color" for that word.
#     style: "outline" adds a stroke around each word; "plain"/"highlight" (text only,
#            the highlight box itself is drawn separately by the caller).
#     """
#     from PIL import Image, ImageDraw, ImageFont
#
#     font = ImageFont.truetype(font_path, font_size)
#     probe = Image.new("RGBA", (10, 10))
#     draw = ImageDraw.Draw(probe)
#
#     space_w = draw.textlength(" ", font=font)
#     ascent, descent = font.getmetrics()
#     line_height = ascent + descent
#
#     # measure each word
#     measured = []
#     for w in words:
#         w_width = draw.textlength(w["text"], font=font)
#         measured.append({**w, "width": w_width})
#
#     # greedy word-wrap into lines that fit max_width
#     lines = []
#     current = []
#     current_w = 0
#     for w in measured:
#         extra = space_w if current else 0
#         if current and current_w + extra + w["width"] > max_width:
#             lines.append(current)
#             current = [w]
#             current_w = w["width"]
#         else:
#             current.append(w)
#             current_w += extra + w["width"]
#     if current:
#         lines.append(current)
#     if not lines:
#         lines = [[]]
#
#     line_gap = int(line_height * 0.25)
#     total_h = len(lines) * line_height + (len(lines) - 1) * line_gap
#     total_w = max(
#         (sum(w["width"] for w in line) + space_w * max(len(line) - 1, 0))
#         for line in lines
#     )
#     total_w = max(total_w, 1)
#
#     pad = stroke_width + 6 if crop_to_ink else stroke_width
#     img_w = int(total_w) + pad * 2
#     img_h = int(total_h) + pad * 2
#     img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
#     draw = ImageDraw.Draw(img)
#
#     y = pad
#     for line in lines:
#         line_w = sum(w["width"] for w in line) + space_w * max(len(line) - 1, 0)
#         x = pad + (total_w - line_w) / 2
#         for w in line:
#             color = w["color"] if w["color"] else default_color
#             if style == "outline" and stroke_width > 0:
#                 draw.text((x, y), w["text"], font=font, fill=color,
#                            stroke_width=stroke_width, stroke_fill=stroke_color)
#             else:
#                 draw.text((x, y), w["text"], font=font, fill=color)
#             x += w["width"] + space_w
#         y += line_height + line_gap
#
#     # Tight-crop to the actual ink bounding box (alpha channel), the same way
#     # the normal (non-colored) highlight path crops based on the TextClip mask.
#     # Font metrics (ascent+descent) always leave extra vertical breathing room
#     # that the mask-based crop doesn't have — without this crop, multicolor
#     # cards come out a few px taller than normal cards and the position math
#     # (which anchors off clip height) ends up placing them slightly higher.
#     if crop_to_ink:
#         alpha = img.split()[-1]
#         bbox = alpha.getbbox()
#         if bbox:
#             img = img.crop(bbox)
#         img_w, img_h = img.size
#
#     return img, (img_w, img_h)
#
#
# FONT_MAP = {
#     "Anton": "fonts/Anton-Regular.ttf",
#     "BarlowCondensed-Black": "fonts/BarlowCondensed-Black.ttf",
#     "LilitaOne-Regular" : "fonts/LilitaOne-Regular.ttf",
#     "Impact":       "C:/Windows/Fonts/impact.ttf",
#     "Arial Black":  "C:/Windows/Fonts/ariblk.ttf",
#     "Arial Bold":   "C:/Windows/Fonts/arialbd.ttf",
#     "Calibri Bold": "C:/Windows/Fonts/calibrib.ttf",
#     "Candara Bold": "C:/Windows/Fonts/Candarab.ttf",
#     "Comic Sans":   "C:/Windows/Fonts/comicbd.ttf",
#     "Bahnschrift":  "C:/Windows/Fonts/bahnschrift.ttf",
# }
# ARABIC_FONT = "fonts/NotoNaskhArabic-Regular.ttf"
#
#
# # ─────────────────────────────────────────────────────────────
# # VIDEO UPLOAD (Mode 1 — browse from device, replaces typed path)
# # ─────────────────────────────────────────────────────────────
# @app.route("/upload-video", methods=["POST"])
# def upload_video():
#     """Accepts the main source video for Mode 1 (Single Long Video)."""
#     if "file" not in request.files:
#         return jsonify({"error": "No file provided"}), 400
#
#     f = request.files["file"]
#     video_id = str(uuid.uuid4())
#     ext = os.path.splitext(f.filename)[1] or ".mp4"
#     save_path = os.path.join(UPLOAD_FOLDER, f"{video_id}{ext}")
#     f.save(save_path)
#
#     duration = get_video_duration(save_path)
#     if duration is None:
#         os.remove(save_path)
#         return jsonify({"error": "Could not read video file — is it a valid video?"}), 400
#
#     print(f"[UPLOAD] Video saved: {save_path} ({duration:.1f}s)")
#
#     return jsonify({
#         "video_id": video_id,
#         "filename": f.filename,
#         "path":     save_path,
#         "duration": duration,
#     })
#
#
# # ─────────────────────────────────────────────────────────────
# # LOGO UPLOAD (Mode 1 & Mode 2 — browse from device, replaces typed path)
# # ─────────────────────────────────────────────────────────────
# @app.route("/upload-logo", methods=["POST"])
# def upload_logo():
#     """Accepts a logo image (PNG recommended) used in the render step."""
#     if "file" not in request.files:
#         return jsonify({"error": "No file provided"}), 400
#
#     f = request.files["file"]
#     logo_id = str(uuid.uuid4())
#     ext = os.path.splitext(f.filename)[1] or ".png"
#     save_path = os.path.join(UPLOAD_FOLDER, f"{logo_id}{ext}")
#     f.save(save_path)
#
#     print(f"[UPLOAD] Logo saved: {save_path}")
#
#     return jsonify({
#         "logo_id":  logo_id,
#         "filename": f.filename,
#         "path":     save_path,
#     })
#
#
# # ─────────────────────────────────────────────────────────────
# # CLIP UPLOAD (Mode 2 — drag & drop)
# # ─────────────────────────────────────────────────────────────
# @app.route("/upload-clip", methods=["POST"])
# def upload_clip():
#     """Accepts a single video file upload, saves it, returns its id/path/duration."""
#     if "file" not in request.files:
#         return jsonify({"error": "No file provided"}), 400
#
#     f = request.files["file"]
#     clip_id = str(uuid.uuid4())
#     ext = os.path.splitext(f.filename)[1] or ".mp4"
#     save_path = os.path.join(CLIPS_FOLDER, f"{clip_id}{ext}")
#     f.save(save_path)
#
#     duration = get_video_duration(save_path)
#     if duration is None:
#         os.remove(save_path)
#         return jsonify({"error": "Could not read video file — is it a valid video?"}), 400
#
#     print(f"[UPLOAD] Clip saved: {save_path} ({duration:.1f}s)")
#
#     return jsonify({
#         "clip_id":  clip_id,
#         "filename": f.filename,
#         "path":     save_path,
#         "duration": duration,
#     })
#
#
# @app.route("/upload-audio", methods=["POST"])
# def upload_audio():
#     """Accepts a single audio file upload (for Mode 2.2 — replaces clip audio + gets transcribed)."""
#     if "file" not in request.files:
#         return jsonify({"error": "No file provided"}), 400
#
#     f = request.files["file"]
#     audio_id = str(uuid.uuid4())
#     ext = os.path.splitext(f.filename)[1] or ".mp3"
#     save_path = os.path.join(UPLOAD_FOLDER, f"{audio_id}{ext}")
#     f.save(save_path)
#
#     duration = get_video_duration(save_path)  # ffprobe works on audio too
#
#     print(f"[UPLOAD] Audio saved: {save_path} ({duration})")
#
#     return jsonify({
#         "audio_id": audio_id,
#         "filename": f.filename,
#         "path":     save_path,
#         "duration": duration,
#     })
#
#
# @app.route("/upload-music", methods=["POST"])
# def upload_music():
#     """Accepts background music file upload (used in both 2.1 and 2.2)."""
#     if "file" not in request.files:
#         return jsonify({"error": "No file provided"}), 400
#
#     f = request.files["file"]
#     music_id = str(uuid.uuid4())
#     ext = os.path.splitext(f.filename)[1] or ".mp3"
#     save_path = os.path.join(UPLOAD_FOLDER, f"{music_id}{ext}")
#     f.save(save_path)
#
#     print(f"[UPLOAD] Music saved: {save_path}")
#
#     return jsonify({
#         "music_id": music_id,
#         "filename": f.filename,
#         "path":     save_path,
#     })
#
#
# # ─────────────────────────────────────────────────────────────
# # MODE 1: ORIGINAL LONG-VIDEO TRANSCRIBE FLOW (unchanged)
# # ─────────────────────────────────────────────────────────────
# @app.route("/transcribe", methods=["POST"])
# def transcribe():
#     data = request.get_json()
#     if not data or "video_path" not in data:
#         return jsonify({"error": "No video_path provided"}), 400
#
#     video_path = data["video_path"].strip()
#     segments = data.get("segments", [])
#     words_per_card = int(data.get("wordsPerCard", 2))
#
#     if not segments:
#         return jsonify({"error": "No timestamp segments provided"}), 400
#
#     if not os.path.exists(video_path):
#         return jsonify({"error": f"File not found: {video_path}"}), 400
#
#     job_id = str(uuid.uuid4())
#     jobs[job_id] = {
#         "status": "cropping", "progress": 5,
#         "start_time": time.time(), "chunks": [],
#         "cropped_path": None, "output": None, "error": None,
#         "phase": "transcribe", "mode": "single",
#         "source_paths": [video_path],
#     }
#
#     def do_transcribe():
#         try:
#             print(f"\n{'='*50}")
#             print(f"[TRANSCRIBE] Job started: {job_id[:8]}...")
#             print(f"[TRANSCRIBE] Video: {video_path}")
#             print(f"{'='*50}")
#
#
#             jobs[job_id]["status"]   = "cropping"
#             jobs[job_id]["progress"] = 10
#
#             print(f"[1/3] Cropping {len(segments)} segment(s)...")
#             segment_paths = []
#
#             for i, seg in enumerate(segments):
#                 seg_start = time_str_to_seconds(seg.get("startTime", "0:00"))
#                 seg_end_raw = seg.get("endTime", "")
#                 seg_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_seg{i}.mp4")
#
#                 crop_cmd = ["ffmpeg", "-ss", str(seg_start), "-i", video_path]
#                 if seg_end_raw:
#                     seg_end = time_str_to_seconds(seg_end_raw)
#                     crop_cmd += ["-t", str(seg_end - seg_start)]
#                 crop_cmd += [
#                     "-vf", f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
#                            f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,setsar=1",
#                     "-c:v", "libx264", "-preset", "ultrafast",
#                     "-c:a", "aac",
#                     seg_path, "-y"
#                 ]
#                 subprocess.run(crop_cmd, check=True, capture_output=True)
#                 segment_paths.append(seg_path)
#                 print(f"[1/3]   ✓ Segment {i + 1}/{len(segments)} cropped")
#
#             cropped_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_crop.mp4")
#
#             if len(segment_paths) == 1:
#                 os.replace(segment_paths[0], cropped_path)
#             else:
#                 input_args = []
#                 for p in segment_paths:
#                     input_args += ["-i", p]
#
#                 filter_parts = []
#                 concat_refs = ""
#                 for i in range(len(segment_paths)):
#                     filter_parts.append(f"[{i}:v][{i}:a]")
#                     concat_refs += f"[{i}:v][{i}:a]"
#                 filter_complex = "".join(f"[{i}:v][{i}:a]" for i in range(len(segment_paths))) \
#                                  + f"concat=n={len(segment_paths)}:v=1:a=1[outv][outa]"
#
#                 concat_cmd = [
#                     "ffmpeg", *input_args,
#                     "-filter_complex", filter_complex,
#                     "-map", "[outv]", "-map", "[outa]",
#                     "-c:v", "libx264", "-preset", "ultrafast",
#                     "-c:a", "aac",
#                     cropped_path, "-y"
#                 ]
#                 subprocess.run(concat_cmd, check=True, capture_output=True)
#
#             print(f"[1/3] ✓ Merged → {cropped_path}")
#
#             jobs[job_id]["cropped_path"] = cropped_path
#             jobs[job_id]["progress"]     = 25
#
#             print(f"\n[2/3] Extracting audio...")
#             jobs[job_id]["status"] = "extracting_audio"
#             audio_path = os.path.join(UPLOAD_FOLDER, f"{job_id}.wav")
#             subprocess.run([
#                 "ffmpeg", "-i", cropped_path,
#                 "-vn", "-ar", "16000", "-ac", "1",
#                 "-f", "wav", audio_path, "-y"
#             ], check=True, capture_output=True)
#             print(f"[2/3] ✓ Audio extracted → {audio_path}")
#
#             jobs[job_id]["progress"] = 40
#
#             print(f"\n[3/3] Whisper transcribing...")
#             jobs[job_id]["status"] = "transcribing"
#             result = model.transcribe(audio_path, word_timestamps=True, language="en")
#
#             all_words = extract_words_from_whisper_result(result)
#             import re
#
#             capitalize_next = True
#
#             for word in all_words:
#                 text = word["word"]
#
#                 # Find the first alphabetic character in the word
#                 for i, ch in enumerate(text):
#                     if ch.isalpha():
#                         if capitalize_next:
#                             text = text[:i] + ch.upper() + text[i + 1:]
#                             capitalize_next = False
#                         break
#
#                 word["word"] = text
#
#                 # If this word ends a sentence, capitalize the next word
#                 if re.search(r'[.!?]["\')\]]*$', text):
#                     capitalize_next = True
#
#             chunks = group_words(all_words, max_words=words_per_card)
#             os.remove(audio_path)
#
#             print(f"[3/3] ✓ Transcription complete — {len(chunks)} subtitle cards generated")
#             print(f"\n→ Waiting for user review...\n")
#
#             jobs[job_id]["status"]   = "awaiting_confirmation"
#             jobs[job_id]["progress"] = 100
#             jobs[job_id]["chunks"]   = chunks
#
#         except Exception as e:
#             import traceback
#             tb = traceback.format_exc()
#             print(f"[ERROR] Transcription failed: {e}\n{tb}")
#             jobs[job_id]["status"] = "error"
#             jobs[job_id]["error"]  = str(e) + "\n" + tb
#
#     thread = threading.Thread(target=do_transcribe)
#     thread.daemon = True
#     thread.start()
#     return jsonify({"job_id": job_id})
#
#
# def extract_words_from_whisper_result(result):
#     all_words = []
#     for seg in result["segments"]:
#         if "words" in seg:
#             for w in seg["words"]:
#                 if w.get("word", "").strip():
#                     all_words.append(w)
#
#     if not all_words:
#         for seg in result["segments"]:
#             words = seg["text"].strip().split()
#             dur   = (seg["end"] - seg["start"]) / max(len(words), 1)
#             for i, word in enumerate(words):
#                 all_words.append({
#                     "word":  word,
#                     "start": seg["start"] + i * dur,
#                     "end":   seg["start"] + (i + 1) * dur,
#                 })
#     return all_words
#
#
# # ─────────────────────────────────────────────────────────────
# # MODE 2: MERGE CLIPS (Audio Transcription)
# # ─────────────────────────────────────────────────────────────
# @app.route("/merge-clips", methods=["POST"])
# def merge_clips():
#     """
#     Body:
#     {
#       "clip_paths": ["uploads/clips/a.mp4", "uploads/clips/b.mp4", ...],  # in user-selected order
#       "subtitleMode": "manual" | "transcribe",
#
#       # if manual:
#       "manualText": "the whole subtitle text the user typed",
#       "wordsPerCard": 2,
#       "secondsPerCard": 1.5,
#       "showWholeText": false,   # if true, show entire manualText as one card for full duration
#
#       # if transcribe:
#       "audio_path": "uploads/xxxx.mp3",   # REPLACES original clip audio
#       "wordsPerCard": 2,
#
#       "musicPath": ""   # optional, either mode
#     }
#     """
#     data = request.get_json()
#     clip_paths   = data.get("clip_paths", [])
#     sub_mode     = data.get("subtitleMode", "manual")
#
#     if not clip_paths:
#         return jsonify({"error": "No clips provided"}), 400
#     for p in clip_paths:
#         if not os.path.exists(p):
#             return jsonify({"error": f"Clip not found: {p}"}), 400
#
#     job_id = str(uuid.uuid4())
#     source_paths = list(clip_paths)
#     if data.get("audio_path"):
#         source_paths.append(data.get("audio_path").strip())
#
#     jobs[job_id] = {
#         "status": "merging", "progress": 5,
#         "start_time": time.time(), "chunks": [],
#         "cropped_path": None, "output": None, "error": None,
#         "phase": "transcribe", "mode": "clips",
#         "source_paths": source_paths,
#     }
#
#     def do_merge():
#         try:
#             print(f"\n{'='*50}")
#             print(f"[MERGE] Job started: {job_id[:8]}...")
#             print(f"[MERGE] Clips ({len(clip_paths)}): {clip_paths}")
#             print(f"[MERGE] Subtitle mode: {sub_mode}")
#             print(f"{'='*50}")
#
#             # ── Step 1: concat clips in order ──────────────
#             jobs[job_id]["status"]   = "merging"
#             jobs[job_id]["progress"] = 10
#
#             merged_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_merged.mp4")
#
#             print("[1/3] Concatenating clips (filter-based concat — handles mismatched sources)...")
#
#             input_args = []
#             for p in clip_paths:
#                 input_args += ["-i", p]
#
#             filter_parts = []
#             concat_refs = ""
#             for i in range(len(clip_paths)):
#                 filter_parts.append(
#                     f"[{i}:v]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
#                     f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}];"
#                 )
#                 concat_refs += f"[v{i}]"
#
#             filter_complex = "".join(filter_parts) + f"{concat_refs}concat=n={len(clip_paths)}:v=1:a=0[outv]"
#
#             concat_cmd = [
#                 "ffmpeg",
#                 *input_args,
#                 "-filter_complex", filter_complex,
#                 "-map", "[outv]",
#                 "-an",
#                 "-c:v", "libx264", "-preset", "ultrafast",
#                 merged_path, "-y"
#             ]
#
#             subprocess.run(concat_cmd, check=True, capture_output=True)
#             print(f"[1/3] ✓ Merged → {merged_path}")
#
#             merged_duration = get_video_duration(merged_path)
#             print(f"[1/3] Merged duration: {merged_duration:.1f}s")
#
#             jobs[job_id]["progress"] = 30
#
#             # ── Step 2: handle audio replacement (2.2 only) ──
#             audio_path = data.get("audio_path", "").strip()
#             final_video_path = merged_path
#
#             if sub_mode == "transcribe" and audio_path and os.path.exists(audio_path):
#                 print("\n[2/3] Replacing clip audio with uploaded audio...")
#                 jobs[job_id]["status"] = "extracting_audio"
#
#                 audio_duration = get_video_duration(audio_path)
#                 print(f"[2/3] Uploaded audio duration: {audio_duration:.1f}s")
#                 print(f"[2/3] Merged video duration: {merged_duration:.1f}s")
#
#                 replaced_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_audioswap.mp4")
#
#                 if audio_duration > merged_duration:
#                     pad_amount = audio_duration - merged_duration
#                     print(f"[2/3] Audio longer by {pad_amount:.1f}s — freezing last frame to extend video")
#                     replace_cmd = [
#                         "ffmpeg",
#                         "-i", merged_path,
#                         "-i", audio_path,
#                         "-map", "0:v:0", "-map", "1:a:0",
#                         "-vf", f"tpad=stop_mode=clone:stop_duration={pad_amount}",
#                         "-c:v", "libx264", "-preset", "ultrafast",
#                         "-c:a", "aac",
#                         "-shortest",
#                         replaced_path, "-y"
#                     ]
#                 else:
#                     print(f"[2/3] Video longer than (or equal to) audio — padding audio with silence")
#                     replace_cmd = [
#                         "ffmpeg",
#                         "-i", merged_path,
#                         "-i", audio_path,
#                         "-map", "0:v:0", "-map", "1:a:0",
#                         "-af", "apad",
#                         "-c:v", "copy", "-c:a", "aac",
#                         "-t", str(merged_duration),
#                         replaced_path, "-y"
#                     ]
#
#                 subprocess.run(replace_cmd, check=True, capture_output=True)
#                 final_video_path = replaced_path
#                 final_duration = get_video_duration(replaced_path)
#                 print(f"[2/3] ✓ Audio replaced → {replaced_path} (final duration: {final_duration:.1f}s)")
#             else:
#                 print("\n[2/3] No audio replacement (manual subtitle mode or no audio provided)")
#
#             jobs[job_id]["cropped_path"] = final_video_path  # reuse existing field name for render step
#             jobs[job_id]["progress"] = 45
#
#             # ── Step 3: build subtitle chunks ──────────────
#             if sub_mode == "transcribe" and audio_path and os.path.exists(audio_path):
#                 print("\n[3/3] Whisper transcribing uploaded audio...")
#                 jobs[job_id]["status"] = "transcribing"
#                 words_per_card = int(data.get("wordsPerCard", 2))
#
#                 # Whisper needs wav at 16k mono — re-extract from the audio file directly
#                 wav_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_whisper.wav")
#                 subprocess.run([
#                     "ffmpeg", "-i", audio_path,
#                     "-vn", "-ar", "16000", "-ac", "1",
#                     "-f", "wav", wav_path, "-y"
#                 ], check=True, capture_output=True)
#
#                 result = model.transcribe(wav_path, word_timestamps=True, language="en")
#                 all_words = extract_words_from_whisper_result(result)
#                 chunks = group_words(all_words, max_words=words_per_card)
#                 os.remove(wav_path)
#
#                 print(f"[3/3] ✓ Transcription complete — {len(chunks)} subtitle cards")
#
#             else:
#                 print("\n[3/3] Building manual subtitle chunks...")
#                 jobs[job_id]["status"] = "transcribing"  # reuse same status label for UI consistency
#
#                 manual_text     = data.get("manualText", "").strip()
#                 words_per_card  = int(data.get("wordsPerCard", 2))
#                 seconds_per_card = float(data.get("secondsPerCard", 1.5))
#                 show_whole_text  = bool(data.get("showWholeText", False))
#
#                 if not manual_text:
#                     chunks = []
#                 elif show_whole_text:
#                     chunks = [{
#                         "start": 0.0,
#                         "end":   merged_duration,
#                         "text":  manual_text,
#                     }]
#                 else:
#                     words = manual_text.split()
#                     chunks = []
#                     t = 0.0
#                     i = 0
#                     while i < len(words):
#                         group = words[i: i + words_per_card]
#                         chunk_text = " ".join(group)
#                         chunk_end  = min(t + seconds_per_card, merged_duration)
#                         chunks.append({
#                             "start": t,
#                             "end":   chunk_end,
#                             "text":  chunk_text,
#                         })
#                         t += seconds_per_card
#                         i += words_per_card
#                         if t >= merged_duration:
#                             break
#
#                 print(f"[3/3] ✓ {len(chunks)} manual subtitle cards built "
#                       f"({'whole text' if show_whole_text else f'{words_per_card} words / {seconds_per_card}s'})")
#
#             jobs[job_id]["status"]   = "awaiting_confirmation"
#             jobs[job_id]["progress"] = 100
#             jobs[job_id]["chunks"]   = chunks
#
#             print(f"\n→ Waiting for user review...\n")
#
#         except Exception as e:
#             import traceback
#             tb = traceback.format_exc()
#             print(f"[ERROR] Merge failed: {e}\n{tb}")
#             jobs[job_id]["status"] = "error"
#             jobs[job_id]["error"]  = str(e) + "\n" + tb
#
#     thread = threading.Thread(target=do_merge)
#     thread.daemon = True
#     thread.start()
#     return jsonify({"job_id": job_id})
#
#
# # ─────────────────────────────────────────────────────────────
# # PHASE 2: RENDER  (shared by Mode 1 AND Mode 2 — unchanged logic,
# # just reads jobs[job_id]["cropped_path"] same as before)
# #
# # NEW: each chunk may now carry a "wordColors" dict of
# #      { "<word_index>": "#RRGGBB" } for per-word color overrides.
# # ─────────────────────────────────────────────────────────────
# @app.route("/render", methods=["POST"])
# def render():
#     data   = request.get_json()
#     job_id = data.get("job_id")
#
#     if not job_id or job_id not in jobs:
#         return jsonify({"error": "Invalid job_id"}), 400
#     if jobs[job_id]["status"] != "awaiting_confirmation":
#         return jsonify({"error": "Job not ready for rendering"}), 400
#
#     edited_chunks = data.get("chunks", jobs[job_id]["chunks"])
#     jobs[job_id]["chunks"] = edited_chunks
#
#     font_size_raw = data.get("fontSize", 72)
#
#     print(f"\n{'='*50}")
#     print(f"[RENDER] Job: {job_id[:8]}...")
#     print(f"[RENDER] font       = {data.get('font', 'Impact')}")
#     print(f"[RENDER] fontSize   = {font_size_raw}")
#     print(f"[RENDER] style      = {data.get('style', 'highlight')}")
#     print(f"[RENDER] position   = {data.get('position', 'bottom')}")
#     print(f"[RENDER] logoPath   = {data.get('logoPath', 'none')}")
#     print(f"[RENDER] logoSize   = {data.get('logoSize', 80)}")
#     print(f"[RENDER] musicPath  = {data.get('musicPath', 'none')}")
#     print(f"[RENDER] musicVol   = {data.get('musicVolume', 0.3)}")
#     print(f"[RENDER] chunks     = {len(edited_chunks)}")
#     print(f"{'='*50}\n")
#
#     options = {
#         "font":               data.get("font", "Impact"),
#         "fontSize":           int(font_size_raw),
#         "textColor":          data.get("textColor", "#FFFFFF"),
#         "highlightColor":     data.get("highlightColor", "#F5A623"),
#         "highlightTextColor": data.get("highlightTextColor", "#000000"),
#         "position":           data.get("position", "bottom"),
#         "style":              data.get("style", "highlight"),
#         "logoPath":           data.get("logoPath", ""),
#         "logoPosition":       data.get("logoPosition", "topright"),
#         "logoSize":           int(data.get("logoSize", 80)),
#         "musicPath":          data.get("musicPath", ""),
#         "musicVolume":        float(data.get("musicVolume", 0.3)),
#     }
#     jobs[job_id]["logo_path"] = options["logoPath"]
#     jobs[job_id]["music_path"] = options["musicPath"]
#
#     jobs[job_id]["status"]     = "rendering"
#     jobs[job_id]["progress"]   = 0
#     jobs[job_id]["start_time"] = time.time()
#     jobs[job_id]["phase"]      = "render"
#
#     def do_render():
#         try:
#             from moviepy import (
#                 VideoFileClip, TextClip, CompositeVideoClip,
#                 ImageClip, AudioFileClip, CompositeAudioClip
#             )
#             import proglog
#             import numpy as np
#             from PIL import Image, ImageDraw, ImageFont
#
#             font_name  = options["font"]
#             font_size  = options["fontSize"]
#             style      = options["style"]
#             position   = options["position"]
#             base_font_file = FONT_MAP.get(font_name, "C:/Windows/Fonts/impact.ttf")
#
#             if not os.path.exists(base_font_file):
#                 print(f"[WARN] Font not found: {base_font_file} → using impact.ttf")
#                 base_font_file = "C:/Windows/Fonts/impact.ttf"
#
#             text_rgb    = hex_to_rgb(options["textColor"])
#             hl_bg_rgb   = hex_to_rgb(options["highlightColor"])
#             hl_text_rgb = hex_to_rgb(options["highlightTextColor"])
#
#             cropped_path = jobs[job_id]["cropped_path"]
#             video        = VideoFileClip(cropped_path)
#             W, H         = video.size
#             total_dur    = video.duration
#
#             print(f"[RENDER] Video loaded: {W}x{H}, {total_dur:.1f}s")
#
#             font_size_scaled = font_size
#             print(f"[RENDER] Font size: {font_size_scaled}px (no scaling)")
#
#             jobs[job_id]["progress"] = 10
#
#             # ── Step 1: Build subtitle clips ───────────────
#             print(f"\n[1/4] Building {len(jobs[job_id]['chunks'])} subtitle clips...")
#             subtitle_clips = []
#             chunks = jobs[job_id]["chunks"]
#
#             max_text_w = int(W * 0.88)
#
#             for idx, chunk in enumerate(chunks):
#                 raw_txt = chunk["text"]
#                 has_arabic = contains_arabic(raw_txt)
#
#                 # NEW: per-word color overrides for this chunk (word_index -> RGB tuple)
#                 word_colors = parse_word_colors(chunk.get("wordColors"))
#                 use_multicolor = bool(word_colors) and not has_arabic
#
#                 if has_arabic:
#                     txt = shape_arabic_text(raw_txt)
#                     active_font_file = ARABIC_FONT if os.path.exists(ARABIC_FONT) else base_font_file
#                     if not os.path.exists(ARABIC_FONT):
#                         print(f"[WARN] Arabic font not found at {ARABIC_FONT} — falling back, glyphs may break")
#                 else:
#                     txt = raw_txt
#                     active_font_file = base_font_file
#
#                 start = float(chunk["start"])
#                 end   = min(float(chunk["end"]), total_dur)
#                 end   = max(end, start + 0.2)
#                 dur   = end - start
#
#                 if use_multicolor:
#                     # ── NEW PATH: render each word with its own color via PIL ──
#                     words_list = raw_txt.split()
#                     words_data = [
#                         {"text": w, "color": word_colors.get(i)}
#                         for i, w in enumerate(words_list)
#                     ]
#
#                     try:
#                         if style == "highlight":
#                             text_img, (txt_w, txt_h) = build_multicolor_text_image(
#                                 words_data, active_font_file, font_size_scaled,
#                                 default_color=hl_text_rgb, style="plain",
#                                 max_width=max_text_w,
#                             )
#                             pad_x = 30
#                             pad_y = max(6, int(font_size_scaled * 0.25))
#                             box_w = txt_w + pad_x * 2
#                             box_h = txt_h + pad_y * 2
#                             radius = min(box_h // 2, 24)
#
#                             box_img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
#                             bdraw = ImageDraw.Draw(box_img)
#                             bdraw.rounded_rectangle(
#                                 [(0, 0), (box_w - 1, box_h - 1)],
#                                 radius=radius,
#                                 fill=(hl_bg_rgb[0], hl_bg_rgb[1], hl_bg_rgb[2], 255)
#                             )
#                             box_img.paste(text_img, (pad_x, pad_y), text_img)
#
#                             combo_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_wc_{idx}.png")
#                             box_img.save(combo_path)
#                             tc = ImageClip(combo_path, duration=dur)
#
#                         elif style == "outline":
#                             text_img, (tw, th) = build_multicolor_text_image(
#                                 words_data, active_font_file, font_size_scaled,
#                                 default_color=text_rgb, style="outline",
#                                 stroke_width=5, max_width=max_text_w,
#                                 crop_to_ink=False,
#                             )
#                             # Match the margin=(30, 50) TextClip uses on the
#                             # non-colored outline path so clip height (and
#                             # therefore vertical position) lines up exactly.
#                             mx, my = 30, 50
#                             padded = Image.new("RGBA", (tw + mx * 2, th + my * 2), (0, 0, 0, 0))
#                             padded.paste(text_img, (mx, my), text_img)
#                             combo_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_wc_{idx}.png")
#                             padded.save(combo_path)
#                             tc = ImageClip(combo_path, duration=dur)
#
#                         else:  # plain
#                             text_img, (tw, th) = build_multicolor_text_image(
#                                 words_data, active_font_file, font_size_scaled,
#                                 default_color=text_rgb, style="plain",
#                                 max_width=max_text_w,
#                                 crop_to_ink=False,
#                             )
#                             mx, my = 30, 50
#                             padded = Image.new("RGBA", (tw + mx * 2, th + my * 2), (0, 0, 0, 0))
#                             padded.paste(text_img, (mx, my), text_img)
#                             combo_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_wc_{idx}.png")
#                             padded.save(combo_path)
#                             tc = ImageClip(combo_path, duration=dur)
#
#                     except Exception as e:
#                         print(f"[WARN] Multicolor TextClip error on chunk {idx}: {e} → fallback to single color")
#                         use_multicolor = False  # fall through to the normal path below
#
#                 if not use_multicolor:
#                     try:
#                         if style == "highlight":
#                             probe_w = int(W * 0.9)
#                             probe_h = int(font_size_scaled * 2.2)
#
#                             text_only = TextClip(
#                                 font=active_font_file, text=txt,
#                                 font_size=font_size_scaled,
#                                 color=f"rgb{hl_text_rgb}",
#                                 method="caption",
#                                 size=(probe_w, probe_h),
#                                 text_align="center",
#                                 duration=dur,
#                                 transparent=True,
#                             )
#
#                             frame = text_only.get_frame(0)
#                             mask  = text_only.mask.get_frame(0) if text_only.mask else None
#
#                             if mask is not None:
#                                 ys, xs = np.where(mask > 0.01)
#                                 if len(xs) > 0 and len(ys) > 0:
#                                     x_min, x_max = int(xs.min()), int(xs.max())
#                                     y_min, y_max = int(ys.min()), int(ys.max())
#                                     real_txt_w = x_max - x_min + 1
#                                     real_txt_h = y_max - y_min + 1
#                                 else:
#                                     x_min, y_min = 0, 0
#                                     x_max, y_max = probe_w - 1, probe_h - 1
#                                     real_txt_w, real_txt_h = probe_w, probe_h
#                             else:
#                                 x_min, y_min = 0, 0
#                                 x_max, y_max = probe_w - 1, probe_h - 1
#                                 real_txt_w, real_txt_h = probe_w, probe_h
#
#                             pad_x = 30
#                             pad_y = max(6, int(font_size_scaled * 0.25))
#
#                             box_w = real_txt_w + pad_x * 2
#                             box_h = real_txt_h + pad_y * 2
#                             radius = min(box_h // 2, 24)
#
#                             box_img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
#                             draw = ImageDraw.Draw(box_img)
#                             draw.rounded_rectangle(
#                                 [(0, 0), (box_w - 1, box_h - 1)],
#                                 radius=radius,
#                                 fill=(hl_bg_rgb[0], hl_bg_rgb[1], hl_bg_rgb[2], 255)
#                             )
#                             box_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_box_{idx}.png")
#                             box_img.save(box_path)
#
#                             box_clip = ImageClip(box_path, duration=dur)
#
#                             cropped_text = text_only.cropped(
#                                 x1=x_min, y1=y_min, x2=x_max + 1, y2=y_max + 1
#                             )
#
#                             text_x = (box_w - real_txt_w) // 2
#                             text_y = (box_h - real_txt_h) // 2
#
#                             text_clip = cropped_text.with_position((text_x, text_y))
#                             tc = CompositeVideoClip(
#                                 [box_clip, text_clip], size=(box_w, box_h)
#                             ).with_duration(dur)
#
#                         elif style == "outline":
#                             tc = TextClip(
#                                 font=active_font_file, text=txt,
#                                 font_size=font_size_scaled,
#                                 color=f"rgb{text_rgb}",
#                                 stroke_color="black", stroke_width=5,
#                                 margin=(30, 50),
#                                 size=(max_text_w, None),
#                                 method="caption",
#                                 text_align="center",
#                                 duration=dur,
#                                 transparent=True,
#                             )
#                         else:
#                             tc = TextClip(
#                                 font=active_font_file, text=txt,
#                                 font_size=font_size_scaled,
#                                 color=f"rgb{text_rgb}",
#                                 margin=(30, 50),
#                                 size=(max_text_w, None),
#                                 method="caption",
#                                 text_align="center",
#                                 duration=dur,
#                                 transparent=True,
#                             )
#                     except Exception as e:
#                         print(f"[WARN] TextClip error on chunk {idx}: {e} → fallback")
#                         tc = TextClip(
#                             font="C:/Windows/Fonts/impact.ttf",
#                             text=txt, font_size=font_size_scaled,
#                             color=f"rgb{hl_text_rgb}",
#                             bg_color=f"rgb{hl_bg_rgb}",
#                             stroke_width=0, margin=(24, 12),
#                             duration=dur, transparent=False,
#                         )
#
#                 tc_w, tc_h = tc.size
#                 VPAD = max(40, int(H * 0.03))
#
#                 if position == "top":
#                     y = VPAD
#                 elif position == "upper_center":
#                     y = int(H * 0.22)
#                 elif position == "center":
#                     y = (H - tc_h) // 2
#                 elif position == "lower_center":
#                     y = int(H * 0.65)
#                 else:  # bottom
#                     y = H - tc_h - VPAD
#
#                 y = max(VPAD, min(y, H - tc_h - VPAD))
#                 x = max(0, (W - tc_w) // 2)
#
#                 tc = tc.with_position((x, y)).with_start(start)
#                 subtitle_clips.append(tc)
#
#             print(f"[1/4] ✓ {len(subtitle_clips)} subtitle clips built")
#             jobs[job_id]["progress"] = 35
#
#             # ── Step 2: Logo overlay ───────────────────────
#             logo_clip = None
#             logo_path = options["logoPath"].strip()
#             if logo_path and os.path.exists(logo_path):
#                 print(f"\n[2/4] Adding logo overlay...")
#                 logo_size = options["logoSize"]
#                 logo_pos  = options["logoPosition"]
#                 PAD = max(60, int(H * 0.050))
#
#                 logo   = ImageClip(logo_path, duration=total_dur)
#                 lw, lh = logo.size
#                 ratio  = logo_size / max(lw, lh)
#                 new_w  = int(lw * ratio)
#                 logo   = logo.resized(width=new_w)
#
#                 actual_w, actual_h = logo.size
#                 pos_map = {
#                     "topleft":     (PAD,                   PAD),
#                     "topright":    (W - actual_w - PAD,    PAD),
#                     "bottomleft":  (PAD,                   H - actual_h - PAD),
#                     "bottomright": (W - actual_w - PAD,    H - actual_h - PAD),
#                 }
#                 px, py    = pos_map.get(logo_pos, (PAD, PAD))
#                 px        = max(0, min(px, W - actual_w))
#                 py        = max(0, min(py, H - actual_h))
#                 logo_clip = logo.with_position((px, py))
#                 print(f"[2/4] ✓ Logo placed at ({px},{py})")
#             else:
#                 print(f"\n[2/4] No logo — skipping")
#
#             jobs[job_id]["progress"] = 50
#
#             # ── Step 3: Composite video ────────────────────
#             print(f"\n[3/4] Compositing video...")
#             all_clips = [video] + subtitle_clips
#             if logo_clip:
#                 all_clips.append(logo_clip)
#             final_video = CompositeVideoClip(all_clips)
#             print(f"[3/4] ✓ Composite done ({len(all_clips)} layers)")
#
#             # ── Step 4: Background music ───────────────────
#             music_path = options["musicPath"].strip()
#             if music_path and os.path.exists(music_path):
#                 print(f"\n[3.5/4] Adding background music...")
#                 music_vol = options["musicVolume"]
#                 music     = AudioFileClip(music_path)
#
#                 if music.duration < total_dur:
#                     loops = int(total_dur / music.duration) + 1
#                     from moviepy import concatenate_audioclips
#                     music = concatenate_audioclips([music] * loops)
#
#                 music = music.subclipped(0, total_dur)
#
#                 try:
#                     from moviepy.audio.fx import MultiplyVolume
#                     music = music.with_effects([MultiplyVolume(music_vol)])
#                 except Exception as e:
#                     print(f"[WARN] Volume scaling failed: {e}")
#
#                 original_audio = video.audio
#                 if original_audio:
#                     mixed = CompositeAudioClip([original_audio, music])
#                 else:
#                     mixed = music
#
#                 final_video = final_video.with_audio(mixed)
#                 print(f"[3.5/4] ✓ Music mixed")
#             else:
#                 print(f"\n[3.5/4] No background music — skipping")
#
#             jobs[job_id]["progress"] = 70
#             jobs[job_id]["status"]   = "exporting"
#
#             # ── Step 5: Export ─────────────────────────────
#             out_name = f"{job_id}_final.mp4"
#             out_path = os.path.join(OUTPUT_FOLDER, out_name)
#
#             print(f"\n[4/4] Exporting → {out_path}")
#
#             last_printed = [0]
#
#             class ExportLogger(proglog.ProgressBarLogger):
#                 def callback(self, **changes):
#                     for key, value in changes.items():
#                         if key == "index":
#                             bars = self.bars
#                             if "t" in bars:
#                                 total = bars["t"].get("total", 1) or 1
#                                 pct = int((value / total) * 100)
#                                 job_pct = 70 + int(pct * 0.29)
#                                 jobs[job_id]["progress"] = min(job_pct, 99)
#                                 milestone = (pct // 10) * 10
#                                 if milestone > last_printed[0]:
#                                     last_printed[0] = milestone
#                                     elapsed = time.time() - jobs[job_id]["start_time"]
#                                     print(f"[4/4] Export: {pct}% complete ({elapsed:.0f}s elapsed)")
#
#             export_logger = ExportLogger()
#
#             final_video.write_videofile(
#                 out_path,
#                 codec="libx264",
#                 audio_codec="aac",
#                 fps=video.fps,
#                 logger=export_logger,
#                 threads=4,
#                 preset="ultrafast",
#             )
#
#             video.close()
#             final_video.close()
#
#             elapsed_total = time.time() - jobs[job_id]["start_time"]
#             print(f"\n[4/4] ✓ Export complete! ({elapsed_total:.1f}s)")
#
#             jobs[job_id]["status"]   = "done"
#             jobs[job_id]["progress"] = 100
#             jobs[job_id]["output"]   = os.path.abspath(out_path)
#
#             cleanup_job_uploads(job_id)
#
#         except Exception as e:
#             import traceback
#             tb = traceback.format_exc()
#             print(f"\n[ERROR] Render failed: {e}\n{tb}")
#             jobs[job_id]["status"] = "error"
#             jobs[job_id]["error"]  = str(e) + "\n" + tb
#
#     thread = threading.Thread(target=do_render)
#     thread.daemon = True
#     thread.start()
#     return jsonify({"job_id": job_id})
#
#
# @app.route("/status/<job_id>", methods=["GET"])
# def status(job_id):
#     if job_id not in jobs:
#         return jsonify({"error": "Job not found"}), 404
#     job      = jobs[job_id]
#     elapsed  = time.time() - job.get("start_time", time.time())
#     progress = job.get("progress", 0)
#     eta = None
#     if progress > 5:
#         eta = max(0, int(elapsed / (progress / 100) - elapsed))
#     return jsonify({
#         "status":   job["status"],
#         "progress": progress,
#         "eta":      eta,
#         "chunks":   job.get("chunks", []),
#         "output":   job.get("output"),
#         "error":    job.get("error"),
#         "phase":    job.get("phase", "transcribe"),
#     })
#
#
# @app.route("/download/<job_id>", methods=["GET"])
# def download(job_id):
#     if job_id not in jobs or jobs[job_id]["status"] != "done":
#         return jsonify({"error": "File not ready"}), 404
#     return send_file(jobs[job_id]["output"], as_attachment=True, download_name="final_reel.mp4")
#
#
# if __name__ == "__main__":
#     app.run(debug=True, port=5000)



#####################################---------ORIGINAL-----------##############################################










from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import whisper
import subprocess
import os
import uuid
import threading
import time
import re
import glob
import json

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
CLIPS_FOLDER  = "uploads/clips"
OUTPUT_FOLDER = "Outputs"
MODEL_PATH = "Whisper-model/small.pt"
WHISPER_CACHE = os.environ.get("WHISPER_CACHE", None)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CLIPS_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
TARGET_W, TARGET_H = 1080, 1920  # standard reel canvas — keeps sizing consistent across modes



jobs = {}

import gc

model = None
model_lock = threading.Lock()

def get_model():
    """Loads Whisper into RAM only when a job actually needs it. Uses the
    locally bundled file if present (your 250MB file next to app.py), otherwise
    downloads once and caches to WHISPER_CACHE (point this at your Railway Volume)."""
    global model
    if model is None:
        print("[MODEL] Loading Whisper into memory...")
        source = MODEL_PATH if os.path.exists(MODEL_PATH) else "small"
        model = whisper.load_model(source, download_root=WHISPER_CACHE)
        print("[MODEL] Ready.")
    return model

def release_model():
    """Frees Whisper from RAM the moment transcription finishes."""
    global model
    if model is not None:
        print("[MODEL] Releasing Whisper from memory...")
        model = None
        gc.collect()


# ─────────────────────────────────────────────────────────────
# HELPERS (unchanged from your original)
# ─────────────────────────────────────────────────────────────

VALID_TRANSITIONS = {
    "cut", "fade", "fadeblack", "fadewhite", "dissolve",
    "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
    "circlecrop", "circleopen", "circleclose",
    "zoomin", "pixelize", "hblur",
}
TRANSITION_DURATION = 0.5   # seconds — overlap length for real transitions
CUT_DURATION = 0.05         # seconds — near-instant "fade" standing in for a hard cut

def build_transition_filter(video_labels, clip_durations, transitions,
                             audio_labels=None, out_v_prefix="v", out_a_prefix="a"):
    """
    Chains N already-labeled ffmpeg streams together with xfade (and acrossfade
    if audio_labels is given), based on the transition type requested between
    each consecutive pair.

    video_labels   : e.g. ["0:v","1:v","2:v"]  or ["s0","s1","s2"]
    clip_durations : duration of the ORIGINAL clip feeding each label, same order
    transitions    : list of transition ids, length == len(video_labels) - 1
    audio_labels   : parallel audio labels, e.g. ["0:a","1:a"], or None to skip audio

    Returns (filter_complex_str_or_None, final_video_label, final_audio_label_or_None)
    """
    n = len(video_labels)
    if n == 1:
        return None, video_labels[0], (audio_labels[0] if audio_labels else None)

    parts = []
    v_label = video_labels[0]
    a_label = audio_labels[0] if audio_labels else None
    cum_dur = clip_durations[0]

    for i in range(1, n):
        t_type = transitions[i - 1] if i - 1 < len(transitions) else "cut"
        if t_type not in VALID_TRANSITIONS:
            t_type = "cut"
        dur = CUT_DURATION if t_type == "cut" else TRANSITION_DURATION
        xfade_type = "fade" if t_type == "cut" else t_type
        offset = max(cum_dur - dur, 0)

        next_v = f"{out_v_prefix}{i}"
        parts.append(
            f"[{v_label}][{video_labels[i]}]xfade=transition={xfade_type}:"
            f"duration={dur}:offset={offset}[{next_v}]"
        )
        v_label = next_v

        if audio_labels:
            next_a = f"{out_a_prefix}{i}"
            parts.append(f"[{a_label}][{audio_labels[i]}]acrossfade=d={dur}[{next_a}]")
            a_label = next_a

        cum_dur = cum_dur + clip_durations[i] - dur

    return ";".join(parts), v_label, a_label


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def time_str_to_seconds(t):
    parts = t.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return float(t)


def get_video_duration(video_path):
    try:
        r = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ], capture_output=True, text=True, check=True)
        return float(r.stdout.strip())
    except:
        return None


def group_words(words, max_words=2):
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i: i + max_words]
        start = chunk[0]["start"]
        end   = chunk[-1]["end"]
        text  = " ".join(w["word"].strip() for w in chunk)
        chunks.append({"start": start, "end": end, "text": text})
        i += max_words
    return chunks


def contains_arabic(text):
    return bool(re.search(r'[\u0600-\u06FF\u0750-\u077F]', text))

def cleanup_job_uploads(job_id):
    """Deletes every temp/upload file this job used — never touches OUTPUT_FOLDER,
    so the finished render is always safe."""
    job = jobs.get(job_id, {})
    paths_to_remove = list(job.get("source_paths", []))
    if job.get("logo_path"):
        paths_to_remove.append(job["logo_path"])
    if job.get("music_path"):
        paths_to_remove.append(job["music_path"])

    for p in paths_to_remove:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception as e:
            print(f"[CLEANUP] Could not remove {p}: {e}")

    # everything else this job generated (crop/merge/audioswap/whisper-wav/box/wc pngs)
    # was named with the job_id prefix inside UPLOAD_FOLDER
    for f in glob.glob(os.path.join(UPLOAD_FOLDER, f"{job_id}*")):
        try:
            os.remove(f)
        except Exception as e:
            print(f"[CLEANUP] Could not remove {f}: {e}")

    print(f"[CLEANUP] Job {job_id[:8]} uploads wiped (output preserved)")


def shape_arabic_text(text):
    """Reshapes Arabic text for correct glyph joining + RTL display order."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except ImportError:
        print("[WARN] arabic_reshaper/python-bidi not installed — Arabic text may render disconnected")
        return text


# ─────────────────────────────────────────────────────────────
# NEW: per-word color helpers (word-level subtitle emphasis)
# ─────────────────────────────────────────────────────────────
def parse_word_colors(raw_dict):
    """
    Converts a JSON-ish dict of {"0": "#ff0000", "3": "#00ff00"} (word index -> hex)
    coming from the frontend into {0: (255,0,0), 3: (0,255,0)}.
    Silently skips anything malformed instead of failing the whole render.
    """
    parsed = {}
    if not raw_dict:
        return parsed
    for k, v in raw_dict.items():
        try:
            idx = int(k)
            parsed[idx] = hex_to_rgb(v)
        except (ValueError, TypeError):
            continue
    return parsed


def build_multicolor_text_image(words, font_path, font_size, default_color,
                                 style, stroke_width=5, stroke_color=(0, 0, 0),
                                 max_width=900, crop_to_ink=True):
    """
    Renders a (possibly multi-line, word-wrapped) block of text where each word can
    carry its own RGB color override. Returns (PIL.Image RGBA, (width, height)).

    words: list of dicts -> {"text": str, "color": (r,g,b) or None}
           color=None means "use default_color" for that word.
    style: "outline" adds a stroke around each word; "plain"/"highlight" (text only,
           the highlight box itself is drawn separately by the caller).
    """
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype(font_path, font_size)
    probe = Image.new("RGBA", (10, 10))
    draw = ImageDraw.Draw(probe)

    space_w = draw.textlength(" ", font=font)
    ascent, descent = font.getmetrics()
    line_height = ascent + descent

    # measure each word
    measured = []
    for w in words:
        w_width = draw.textlength(w["text"], font=font)
        measured.append({**w, "width": w_width})

    # greedy word-wrap into lines that fit max_width
    lines = []
    current = []
    current_w = 0
    for w in measured:
        extra = space_w if current else 0
        if current and current_w + extra + w["width"] > max_width:
            lines.append(current)
            current = [w]
            current_w = w["width"]
        else:
            current.append(w)
            current_w += extra + w["width"]
    if current:
        lines.append(current)
    if not lines:
        lines = [[]]

    line_gap = int(line_height * 0.25)
    total_h = len(lines) * line_height + (len(lines) - 1) * line_gap
    total_w = max(
        (sum(w["width"] for w in line) + space_w * max(len(line) - 1, 0))
        for line in lines
    )
    total_w = max(total_w, 1)

    pad = stroke_width + 6 if crop_to_ink else stroke_width
    img_w = int(total_w) + pad * 2
    img_h = int(total_h) + pad * 2
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = pad
    for line in lines:
        line_w = sum(w["width"] for w in line) + space_w * max(len(line) - 1, 0)
        x = pad + (total_w - line_w) / 2
        for w in line:
            color = w["color"] if w["color"] else default_color
            if style == "outline" and stroke_width > 0:
                draw.text((x, y), w["text"], font=font, fill=color,
                           stroke_width=stroke_width, stroke_fill=stroke_color)
            else:
                draw.text((x, y), w["text"], font=font, fill=color)
            x += w["width"] + space_w
        y += line_height + line_gap

    # Tight-crop to the actual ink bounding box (alpha channel), the same way
    # the normal (non-colored) highlight path crops based on the TextClip mask.
    # Font metrics (ascent+descent) always leave extra vertical breathing room
    # that the mask-based crop doesn't have — without this crop, multicolor
    # cards come out a few px taller than normal cards and the position math
    # (which anchors off clip height) ends up placing them slightly higher.
    if crop_to_ink:
        alpha = img.split()[-1]
        bbox = alpha.getbbox()
        if bbox:
            img = img.crop(bbox)
        img_w, img_h = img.size

    return img, (img_w, img_h)


FONT_MAP = {
    "Anton": "fonts/Anton-Regular.ttf",
    "BarlowCondensed-Black": "fonts/BarlowCondensed-Black.ttf",
    "BarlowCondensed-Bold": "fonts/BarlowCondensed-Bold.ttf",
    "LilitaOne-Regular" : "fonts/LilitaOne-Regular.ttf",
    "Arial-Black":  "fonts/Arial-Black.ttf",
    "OpenSans-Regular": "fonts/OpenSans-Regular.ttf",
    "Carlito-Bold": "fonts/Carlito-Bold.ttf",
    "ComicNeue-Regular":"fonts/ComicNeue-Regular.ttf",
    "bahnschrift":  "fonts/bahnschrift.TTF",
}
ARABIC_FONT = "fonts/NotoNaskhArabic-Regular.ttf"


# ─────────────────────────────────────────────────────────────
# VIDEO UPLOAD (Mode 1 — browse from device, replaces typed path)
# ─────────────────────────────────────────────────────────────
@app.route("/upload-video", methods=["POST"])
def upload_video():
    """Accepts the main source video for Mode 1 (Single Long Video)."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    video_id = str(uuid.uuid4())
    ext = os.path.splitext(f.filename)[1] or ".mp4"
    save_path = os.path.join(UPLOAD_FOLDER, f"{video_id}{ext}")
    f.save(save_path)

    duration = get_video_duration(save_path)
    if duration is None:
        os.remove(save_path)
        return jsonify({"error": "Could not read video file — is it a valid video?"}), 400

    print(f"[UPLOAD] Video saved: {save_path} ({duration:.1f}s)")

    return jsonify({
        "video_id": video_id,
        "filename": f.filename,
        "path":     save_path,
        "duration": duration,
    })


# ─────────────────────────────────────────────────────────────
# LOGO UPLOAD (Mode 1 & Mode 2 — browse from device, replaces typed path)
# ─────────────────────────────────────────────────────────────
@app.route("/upload-logo", methods=["POST"])
def upload_logo():
    """Accepts a logo image (PNG recommended) used in the render step."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    logo_id = str(uuid.uuid4())
    ext = os.path.splitext(f.filename)[1] or ".png"
    save_path = os.path.join(UPLOAD_FOLDER, f"{logo_id}{ext}")
    f.save(save_path)

    print(f"[UPLOAD] Logo saved: {save_path}")

    return jsonify({
        "logo_id":  logo_id,
        "filename": f.filename,
        "path":     save_path,
    })


# ─────────────────────────────────────────────────────────────
# CLIP UPLOAD (Mode 2 — drag & drop)
# ─────────────────────────────────────────────────────────────
@app.route("/upload-clip", methods=["POST"])
def upload_clip():
    """Accepts a single video file upload, saves it, returns its id/path/duration."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    clip_id = str(uuid.uuid4())
    ext = os.path.splitext(f.filename)[1] or ".mp4"
    save_path = os.path.join(CLIPS_FOLDER, f"{clip_id}{ext}")
    f.save(save_path)

    duration = get_video_duration(save_path)
    if duration is None:
        os.remove(save_path)
        return jsonify({"error": "Could not read video file — is it a valid video?"}), 400

    print(f"[UPLOAD] Clip saved: {save_path} ({duration:.1f}s)")

    return jsonify({
        "clip_id":  clip_id,
        "filename": f.filename,
        "path":     save_path,
        "duration": duration,
    })


@app.route("/upload-audio", methods=["POST"])
def upload_audio():
    """Accepts a single audio file upload (for Mode 2.2 — replaces clip audio + gets transcribed)."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    audio_id = str(uuid.uuid4())
    ext = os.path.splitext(f.filename)[1] or ".mp3"
    save_path = os.path.join(UPLOAD_FOLDER, f"{audio_id}{ext}")
    f.save(save_path)

    duration = get_video_duration(save_path)  # ffprobe works on audio too

    print(f"[UPLOAD] Audio saved: {save_path} ({duration})")

    return jsonify({
        "audio_id": audio_id,
        "filename": f.filename,
        "path":     save_path,
        "duration": duration,
    })


@app.route("/upload-music", methods=["POST"])
def upload_music():
    """Accepts background music file upload (used in both 2.1 and 2.2)."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    music_id = str(uuid.uuid4())
    ext = os.path.splitext(f.filename)[1] or ".mp3"
    save_path = os.path.join(UPLOAD_FOLDER, f"{music_id}{ext}")
    f.save(save_path)

    print(f"[UPLOAD] Music saved: {save_path}")

    return jsonify({
        "music_id": music_id,
        "filename": f.filename,
        "path":     save_path,
    })


# ─────────────────────────────────────────────────────────────
# MODE 1: ORIGINAL LONG-VIDEO TRANSCRIBE FLOW (unchanged)
# ─────────────────────────────────────────────────────────────
@app.route("/transcribe", methods=["POST"])
def transcribe():
    data = request.get_json()
    if not data or "video_path" not in data:
        return jsonify({"error": "No video_path provided"}), 400

    video_path = data["video_path"].strip()
    segments = data.get("segments", [])
    transitions = data.get("transitions", [])
    words_per_card = int(data.get("wordsPerCard", 2))

    if not segments:
        return jsonify({"error": "No timestamp segments provided"}), 400

    if not os.path.exists(video_path):
        return jsonify({"error": f"File not found: {video_path}"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "cropping", "progress": 5,
        "start_time": time.time(), "chunks": [],
        "cropped_path": None, "output": None, "error": None,
        "phase": "transcribe", "mode": "single",
        "source_paths": [video_path],
    }

    def do_transcribe():
        try:
            print(f"\n{'='*50}")
            print(f"[TRANSCRIBE] Job started: {job_id[:8]}...")
            print(f"[TRANSCRIBE] Video: {video_path}")
            print(f"{'='*50}")


            jobs[job_id]["status"]   = "cropping"
            jobs[job_id]["progress"] = 10

            print(f"[1/3] Cropping {len(segments)} segment(s)...")
            segment_paths = []

            for i, seg in enumerate(segments):
                seg_start = time_str_to_seconds(seg.get("startTime", "0:00"))
                seg_end_raw = seg.get("endTime", "")
                seg_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_seg{i}.mp4")

                crop_cmd = ["ffmpeg", "-ss", str(seg_start), "-i", video_path]
                if seg_end_raw:
                    seg_end = time_str_to_seconds(seg_end_raw)
                    crop_cmd += ["-t", str(seg_end - seg_start)]
                crop_cmd += [
                    "-vf", f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
                           f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac",
                    seg_path, "-y"
                ]
                subprocess.run(crop_cmd, check=True, capture_output=True)
                segment_paths.append(seg_path)
                print(f"[1/3]   ✓ Segment {i + 1}/{len(segments)} cropped")

            cropped_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_crop.mp4")

            if len(segment_paths) == 1:
                os.replace(segment_paths[0], cropped_path)
            else:
                seg_durations = [get_video_duration(p) for p in segment_paths]
                video_labels = [f"{i}:v" for i in range(len(segment_paths))]
                audio_labels = [f"{i}:a" for i in range(len(segment_paths))]

                filter_complex, v_out, a_out = build_transition_filter(
                    video_labels, seg_durations, transitions, audio_labels=audio_labels
                )

                input_args = []
                for p in segment_paths:
                    input_args += ["-i", p]

                concat_cmd = [
                    "ffmpeg", *input_args,
                    "-filter_complex", filter_complex,
                    "-map", f"[{v_out}]", "-map", f"[{a_out}]",
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac",
                    cropped_path, "-y"
                ]
                subprocess.run(concat_cmd, check=True, capture_output=True)

            print(f"[1/3] ✓ Merged → {cropped_path}")

            jobs[job_id]["cropped_path"] = cropped_path
            jobs[job_id]["progress"]     = 25

            print(f"\n[2/3] Extracting audio...")
            jobs[job_id]["status"] = "extracting_audio"
            audio_path = os.path.join(UPLOAD_FOLDER, f"{job_id}.wav")
            subprocess.run([
                "ffmpeg", "-i", cropped_path,
                "-vn", "-ar", "16000", "-ac", "1",
                "-f", "wav", audio_path, "-y"
            ], check=True, capture_output=True)
            print(f"[2/3] ✓ Audio extracted → {audio_path}")

            jobs[job_id]["progress"] = 40

            print(f"\n[3/3] Whisper transcribing...")
            jobs[job_id]["status"] = "transcribing"
            with model_lock:
                m = get_model()
                result = m.transcribe(audio_path, word_timestamps=True, language="en")
                release_model()

            all_words = extract_words_from_whisper_result(result)
            import re

            capitalize_next = True

            for word in all_words:
                text = word["word"]

                # Find the first alphabetic character in the word
                for i, ch in enumerate(text):
                    if ch.isalpha():
                        if capitalize_next:
                            text = text[:i] + ch.upper() + text[i + 1:]
                            capitalize_next = False
                        break

                word["word"] = text

                # If this word ends a sentence, capitalize the next word
                if re.search(r'[.!?]["\')\]]*$', text):
                    capitalize_next = True

            chunks = group_words(all_words, max_words=words_per_card)
            os.remove(audio_path)

            print(f"[3/3] ✓ Transcription complete — {len(chunks)} subtitle cards generated")
            print(f"\n→ Waiting for user review...\n")

            jobs[job_id]["status"]   = "awaiting_confirmation"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["chunks"]   = chunks

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[ERROR] Transcription failed: {e}\n{tb}")
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"]  = str(e) + "\n" + tb

    thread = threading.Thread(target=do_transcribe)
    thread.daemon = True
    thread.start()
    return jsonify({"job_id": job_id})


def extract_words_from_whisper_result(result):
    all_words = []
    for seg in result["segments"]:
        if "words" in seg:
            for w in seg["words"]:
                if w.get("word", "").strip():
                    all_words.append(w)

    if not all_words:
        for seg in result["segments"]:
            words = seg["text"].strip().split()
            dur   = (seg["end"] - seg["start"]) / max(len(words), 1)
            for i, word in enumerate(words):
                all_words.append({
                    "word":  word,
                    "start": seg["start"] + i * dur,
                    "end":   seg["start"] + (i + 1) * dur,
                })
    return all_words


# ─────────────────────────────────────────────────────────────
# MODE 2: MERGE CLIPS (Audio Transcription)
# ─────────────────────────────────────────────────────────────
@app.route("/merge-clips", methods=["POST"])
def merge_clips():
    """
    Body:
    {
      "clip_paths": ["uploads/clips/a.mp4", "uploads/clips/b.mp4", ...],  # in user-selected order
      "subtitleMode": "manual" | "transcribe",

      # if manual:
      "manualText": "the whole subtitle text the user typed",
      "wordsPerCard": 2,
      "secondsPerCard": 1.5,
      "showWholeText": false,   # if true, show entire manualText as one card for full duration

      # if transcribe:
      "audio_path": "uploads/xxxx.mp3",   # REPLACES original clip audio
      "wordsPerCard": 2,

      "musicPath": ""   # optional, either mode
    }
    """
    data = request.get_json()
    clip_paths   = data.get("clip_paths", [])
    transitions = data.get("transitions", [])
    sub_mode     = data.get("subtitleMode", "manual")

    if not clip_paths:
        return jsonify({"error": "No clips provided"}), 400
    for p in clip_paths:
        if not os.path.exists(p):
            return jsonify({"error": f"Clip not found: {p}"}), 400

    job_id = str(uuid.uuid4())
    source_paths = list(clip_paths)
    if data.get("audio_path"):
        source_paths.append(data.get("audio_path").strip())

    jobs[job_id] = {
        "status": "merging", "progress": 5,
        "start_time": time.time(), "chunks": [],
        "cropped_path": None, "output": None, "error": None,
        "phase": "transcribe", "mode": "clips",
        "source_paths": source_paths,
    }

    def do_merge():
        try:
            print(f"\n{'='*50}")
            print(f"[MERGE] Job started: {job_id[:8]}...")
            print(f"[MERGE] Clips ({len(clip_paths)}): {clip_paths}")
            print(f"[MERGE] Subtitle mode: {sub_mode}")
            print(f"{'='*50}")

            # ── Step 1: concat clips in order ──────────────
            jobs[job_id]["status"]   = "merging"
            jobs[job_id]["progress"] = 10

            merged_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_merged.mp4")
            print("[1/3] Merging clips with transitions...")

            clip_durations = [get_video_duration(p) for p in clip_paths]

            input_args = []
            for p in clip_paths:
                input_args += ["-i", p]

            # Normalize every clip to the same size/fps first — xfade requires matching streams
            scale_parts = []
            for i in range(len(clip_paths)):
                scale_parts.append(
                    f"[{i}:v]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
                    f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[s{i}]"
                )

            scaled_labels = [f"s{i}" for i in range(len(clip_paths))]
            chain_filter, v_out, _ = build_transition_filter(
                scaled_labels, clip_durations, transitions, audio_labels=None,
                out_v_prefix="vx"
            )

            filter_complex = ";".join(scale_parts)
            if chain_filter:
                filter_complex += ";" + chain_filter

            concat_cmd = [
                "ffmpeg",
                *input_args,
                "-filter_complex", filter_complex,
                "-map", f"[{v_out}]",
                "-an",
                "-c:v", "libx264", "-preset", "ultrafast",
                merged_path, "-y"
            ]

            subprocess.run(concat_cmd, check=True, capture_output=True)
            print(f"[1/3] ✓ Merged → {merged_path}")

            merged_duration = get_video_duration(merged_path)
            print(f"[1/3] Merged duration: {merged_duration:.1f}s")

            jobs[job_id]["progress"] = 30

            # ── Step 2: handle audio replacement (2.2 only) ──
            audio_path = data.get("audio_path", "").strip()
            final_video_path = merged_path

            if sub_mode == "transcribe" and audio_path and os.path.exists(audio_path):
                print("\n[2/3] Replacing clip audio with uploaded audio...")
                jobs[job_id]["status"] = "extracting_audio"

                audio_duration = get_video_duration(audio_path)
                print(f"[2/3] Uploaded audio duration: {audio_duration:.1f}s")
                print(f"[2/3] Merged video duration: {merged_duration:.1f}s")

                replaced_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_audioswap.mp4")

                if audio_duration > merged_duration:
                    pad_amount = audio_duration - merged_duration
                    print(f"[2/3] Audio longer by {pad_amount:.1f}s — freezing last frame to extend video")
                    replace_cmd = [
                        "ffmpeg",
                        "-i", merged_path,
                        "-i", audio_path,
                        "-map", "0:v:0", "-map", "1:a:0",
                        "-vf", f"tpad=stop_mode=clone:stop_duration={pad_amount}",
                        "-c:v", "libx264", "-preset", "ultrafast",
                        "-c:a", "aac",
                        "-shortest",
                        replaced_path, "-y"
                    ]
                else:
                    print(f"[2/3] Video longer than (or equal to) audio — padding audio with silence")
                    replace_cmd = [
                        "ffmpeg",
                        "-i", merged_path,
                        "-i", audio_path,
                        "-map", "0:v:0", "-map", "1:a:0",
                        "-af", "apad",
                        "-c:v", "copy", "-c:a", "aac",
                        "-t", str(merged_duration),
                        replaced_path, "-y"
                    ]

                subprocess.run(replace_cmd, check=True, capture_output=True)
                final_video_path = replaced_path
                final_duration = get_video_duration(replaced_path)
                print(f"[2/3] ✓ Audio replaced → {replaced_path} (final duration: {final_duration:.1f}s)")
            else:
                print("\n[2/3] No audio replacement (manual subtitle mode or no audio provided)")

            jobs[job_id]["cropped_path"] = final_video_path  # reuse existing field name for render step
            jobs[job_id]["progress"] = 45

            # ── Step 3: build subtitle chunks ──────────────
            if sub_mode == "transcribe" and audio_path and os.path.exists(audio_path):
                print("\n[3/3] Whisper transcribing uploaded audio...")
                jobs[job_id]["status"] = "transcribing"
                words_per_card = int(data.get("wordsPerCard", 2))

                # Whisper needs wav at 16k mono — re-extract from the audio file directly
                wav_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_whisper.wav")
                subprocess.run([
                    "ffmpeg", "-i", audio_path,
                    "-vn", "-ar", "16000", "-ac", "1",
                    "-f", "wav", wav_path, "-y"
                ], check=True, capture_output=True)

                with model_lock:
                    m = get_model()
                    result = m.transcribe(wav_path, word_timestamps=True, language="en")
                    release_model()
                all_words = extract_words_from_whisper_result(result)
                chunks = group_words(all_words, max_words=words_per_card)
                os.remove(wav_path)

                print(f"[3/3] ✓ Transcription complete — {len(chunks)} subtitle cards")

            else:
                print("\n[3/3] Building manual subtitle chunks...")
                jobs[job_id]["status"] = "transcribing"  # reuse same status label for UI consistency

                manual_text     = data.get("manualText", "").strip()
                words_per_card  = int(data.get("wordsPerCard", 2))
                seconds_per_card = float(data.get("secondsPerCard", 1.5))
                show_whole_text  = bool(data.get("showWholeText", False))

                if not manual_text:
                    chunks = []
                elif show_whole_text:
                    chunks = [{
                        "start": 0.0,
                        "end":   merged_duration,
                        "text":  manual_text,
                    }]
                else:
                    words = manual_text.split()
                    chunks = []
                    t = 0.0
                    i = 0
                    while i < len(words):
                        group = words[i: i + words_per_card]
                        chunk_text = " ".join(group)
                        chunk_end  = min(t + seconds_per_card, merged_duration)
                        chunks.append({
                            "start": t,
                            "end":   chunk_end,
                            "text":  chunk_text,
                        })
                        t += seconds_per_card
                        i += words_per_card
                        if t >= merged_duration:
                            break

                print(f"[3/3] ✓ {len(chunks)} manual subtitle cards built "
                      f"({'whole text' if show_whole_text else f'{words_per_card} words / {seconds_per_card}s'})")

            jobs[job_id]["status"]   = "awaiting_confirmation"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["chunks"]   = chunks

            print(f"\n→ Waiting for user review...\n")

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[ERROR] Merge failed: {e}\n{tb}")
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"]  = str(e) + "\n" + tb

    thread = threading.Thread(target=do_merge)
    thread.daemon = True
    thread.start()
    return jsonify({"job_id": job_id})


# ─────────────────────────────────────────────────────────────
# PHASE 2: RENDER  (shared by Mode 1 AND Mode 2 — unchanged logic,
# just reads jobs[job_id]["cropped_path"] same as before)
#
# NEW: each chunk may now carry a "wordColors" dict of
#      { "<word_index>": "#RRGGBB" } for per-word color overrides.
# ─────────────────────────────────────────────────────────────
@app.route("/render", methods=["POST"])
def render():
    data   = request.get_json()
    job_id = data.get("job_id")

    if not job_id or job_id not in jobs:
        return jsonify({"error": "Invalid job_id"}), 400
    if jobs[job_id]["status"] != "awaiting_confirmation":
        return jsonify({"error": "Job not ready for rendering"}), 400

    edited_chunks = data.get("chunks", jobs[job_id]["chunks"])
    jobs[job_id]["chunks"] = edited_chunks

    font_size_raw = data.get("fontSize", 72)

    print(f"\n{'='*50}")
    print(f"[RENDER] Job: {job_id[:8]}...")
    print(f"[RENDER] font       = {data.get('font', 'Impact')}")
    print(f"[RENDER] fontSize   = {font_size_raw}")
    print(f"[RENDER] style      = {data.get('style', 'highlight')}")
    print(f"[RENDER] position   = {data.get('position', 'bottom')}")
    print(f"[RENDER] logoPath   = {data.get('logoPath', 'none')}")
    print(f"[RENDER] logoSize   = {data.get('logoSize', 80)}")
    print(f"[RENDER] musicPath  = {data.get('musicPath', 'none')}")
    print(f"[RENDER] musicVol   = {data.get('musicVolume', 0.3)}")
    print(f"[RENDER] chunks     = {len(edited_chunks)}")
    print(f"{'='*50}\n")

    options = {
        "font":               data.get("font", "Impact"),
        "fontSize":           int(font_size_raw),
        "textColor":          data.get("textColor", "#FFFFFF"),
        "highlightColor":     data.get("highlightColor", "#F5A623"),
        "highlightTextColor": data.get("highlightTextColor", "#000000"),
        "position":           data.get("position", "bottom"),
        "style":              data.get("style", "highlight"),
        "logoPath":           data.get("logoPath", ""),
        "logoPosition":       data.get("logoPosition", "topright"),
        "logoSize":           int(data.get("logoSize", 80)),
        "musicPath":          data.get("musicPath", ""),
        "musicVolume":        float(data.get("musicVolume", 0.3)),
    }
    jobs[job_id]["logo_path"] = options["logoPath"]
    jobs[job_id]["music_path"] = options["musicPath"]

    jobs[job_id]["status"]     = "rendering"
    jobs[job_id]["progress"]   = 0
    jobs[job_id]["start_time"] = time.time()
    jobs[job_id]["phase"]      = "render"

    def do_render():
        try:
            from moviepy import (
                VideoFileClip, TextClip, CompositeVideoClip,
                ImageClip, AudioFileClip, CompositeAudioClip
            )
            import proglog
            import numpy as np
            from PIL import Image, ImageDraw, ImageFont

            font_name  = options["font"]
            font_size  = options["fontSize"]
            style      = options["style"]
            position   = options["position"]
            base_font_file = FONT_MAP.get(font_name, "C:/Windows/Fonts/impact.ttf")

            if not os.path.exists(base_font_file):
                print(f"[WARN] Font not found: {base_font_file} → using impact.ttf")
                base_font_file = "C:/Windows/Fonts/impact.ttf"

            text_rgb    = hex_to_rgb(options["textColor"])
            hl_bg_rgb   = hex_to_rgb(options["highlightColor"])
            hl_text_rgb = hex_to_rgb(options["highlightTextColor"])

            cropped_path = jobs[job_id]["cropped_path"]
            video        = VideoFileClip(cropped_path)
            W, H         = video.size
            total_dur    = video.duration

            print(f"[RENDER] Video loaded: {W}x{H}, {total_dur:.1f}s")

            font_size_scaled = font_size
            print(f"[RENDER] Font size: {font_size_scaled}px (no scaling)")

            jobs[job_id]["progress"] = 10

            # ── Step 1: Build subtitle clips ───────────────
            print(f"\n[1/4] Building {len(jobs[job_id]['chunks'])} subtitle clips...")
            subtitle_clips = []
            chunks = jobs[job_id]["chunks"]

            max_text_w = int(W * 0.88)

            for idx, chunk in enumerate(chunks):
                raw_txt = chunk["text"]
                has_arabic = contains_arabic(raw_txt)

                # NEW: per-word color overrides for this chunk (word_index -> RGB tuple)
                word_colors = parse_word_colors(chunk.get("wordColors"))
                use_multicolor = bool(word_colors) and not has_arabic

                if has_arabic:
                    txt = shape_arabic_text(raw_txt)
                    active_font_file = ARABIC_FONT if os.path.exists(ARABIC_FONT) else base_font_file
                    if not os.path.exists(ARABIC_FONT):
                        print(f"[WARN] Arabic font not found at {ARABIC_FONT} — falling back, glyphs may break")
                else:
                    txt = raw_txt
                    active_font_file = base_font_file

                start = float(chunk["start"])
                end   = min(float(chunk["end"]), total_dur)
                end   = max(end, start + 0.2)
                dur   = end - start

                if use_multicolor:
                    # ── NEW PATH: render each word with its own color via PIL ──
                    words_list = raw_txt.split()
                    words_data = [
                        {"text": w, "color": word_colors.get(i)}
                        for i, w in enumerate(words_list)
                    ]

                    try:
                        if style == "highlight":
                            text_img, (txt_w, txt_h) = build_multicolor_text_image(
                                words_data, active_font_file, font_size_scaled,
                                default_color=hl_text_rgb, style="plain",
                                max_width=max_text_w,
                            )
                            pad_x = 30
                            pad_y = max(6, int(font_size_scaled * 0.25))
                            box_w = txt_w + pad_x * 2
                            box_h = txt_h + pad_y * 2
                            radius = min(box_h // 2, 24)

                            box_img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
                            bdraw = ImageDraw.Draw(box_img)
                            bdraw.rounded_rectangle(
                                [(0, 0), (box_w - 1, box_h - 1)],
                                radius=radius,
                                fill=(hl_bg_rgb[0], hl_bg_rgb[1], hl_bg_rgb[2], 255)
                            )
                            box_img.paste(text_img, (pad_x, pad_y), text_img)

                            combo_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_wc_{idx}.png")
                            box_img.save(combo_path)
                            tc = ImageClip(combo_path, duration=dur)

                        elif style == "outline":
                            text_img, (tw, th) = build_multicolor_text_image(
                                words_data, active_font_file, font_size_scaled,
                                default_color=text_rgb, style="outline",
                                stroke_width=5, max_width=max_text_w,
                                crop_to_ink=False,
                            )
                            # Match the margin=(30, 50) TextClip uses on the
                            # non-colored outline path so clip height (and
                            # therefore vertical position) lines up exactly.
                            mx, my = 30, 50
                            padded = Image.new("RGBA", (tw + mx * 2, th + my * 2), (0, 0, 0, 0))
                            padded.paste(text_img, (mx, my), text_img)
                            combo_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_wc_{idx}.png")
                            padded.save(combo_path)
                            tc = ImageClip(combo_path, duration=dur)

                        else:  # plain
                            text_img, (tw, th) = build_multicolor_text_image(
                                words_data, active_font_file, font_size_scaled,
                                default_color=text_rgb, style="plain",
                                max_width=max_text_w,
                                crop_to_ink=False,
                            )
                            mx, my = 30, 50
                            padded = Image.new("RGBA", (tw + mx * 2, th + my * 2), (0, 0, 0, 0))
                            padded.paste(text_img, (mx, my), text_img)
                            combo_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_wc_{idx}.png")
                            padded.save(combo_path)
                            tc = ImageClip(combo_path, duration=dur)

                    except Exception as e:
                        print(f"[WARN] Multicolor TextClip error on chunk {idx}: {e} → fallback to single color")
                        use_multicolor = False  # fall through to the normal path below

                if not use_multicolor:
                    try:
                        if style == "highlight":
                            probe_w = int(W * 0.9)
                            probe_h = int(font_size_scaled * 2.2)

                            text_only = TextClip(
                                font=active_font_file, text=txt,
                                font_size=font_size_scaled,
                                color=f"rgb{hl_text_rgb}",
                                method="caption",
                                size=(probe_w, probe_h),
                                text_align="center",
                                duration=dur,
                                transparent=True,
                            )

                            frame = text_only.get_frame(0)
                            mask  = text_only.mask.get_frame(0) if text_only.mask else None

                            if mask is not None:
                                ys, xs = np.where(mask > 0.01)
                                if len(xs) > 0 and len(ys) > 0:
                                    x_min, x_max = int(xs.min()), int(xs.max())
                                    y_min, y_max = int(ys.min()), int(ys.max())
                                    real_txt_w = x_max - x_min + 1
                                    real_txt_h = y_max - y_min + 1
                                else:
                                    x_min, y_min = 0, 0
                                    x_max, y_max = probe_w - 1, probe_h - 1
                                    real_txt_w, real_txt_h = probe_w, probe_h
                            else:
                                x_min, y_min = 0, 0
                                x_max, y_max = probe_w - 1, probe_h - 1
                                real_txt_w, real_txt_h = probe_w, probe_h

                            pad_x = 30
                            pad_y = max(6, int(font_size_scaled * 0.25))

                            box_w = real_txt_w + pad_x * 2
                            box_h = real_txt_h + pad_y * 2
                            radius = min(box_h // 2, 24)

                            box_img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
                            draw = ImageDraw.Draw(box_img)
                            draw.rounded_rectangle(
                                [(0, 0), (box_w - 1, box_h - 1)],
                                radius=radius,
                                fill=(hl_bg_rgb[0], hl_bg_rgb[1], hl_bg_rgb[2], 255)
                            )
                            box_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_box_{idx}.png")
                            box_img.save(box_path)

                            box_clip = ImageClip(box_path, duration=dur)

                            cropped_text = text_only.cropped(
                                x1=x_min, y1=y_min, x2=x_max + 1, y2=y_max + 1
                            )

                            text_x = (box_w - real_txt_w) // 2
                            text_y = (box_h - real_txt_h) // 2

                            text_clip = cropped_text.with_position((text_x, text_y))
                            tc = CompositeVideoClip(
                                [box_clip, text_clip], size=(box_w, box_h)
                            ).with_duration(dur)

                        elif style == "outline":
                            tc = TextClip(
                                font=active_font_file, text=txt,
                                font_size=font_size_scaled,
                                color=f"rgb{text_rgb}",
                                stroke_color="black", stroke_width=5,
                                margin=(30, 50),
                                size=(max_text_w, None),
                                method="caption",
                                text_align="center",
                                duration=dur,
                                transparent=True,
                            )
                        else:
                            tc = TextClip(
                                font=active_font_file, text=txt,
                                font_size=font_size_scaled,
                                color=f"rgb{text_rgb}",
                                margin=(30, 50),
                                size=(max_text_w, None),
                                method="caption",
                                text_align="center",
                                duration=dur,
                                transparent=True,
                            )
                    except Exception as e:
                        print(f"[WARN] TextClip error on chunk {idx}: {e} → fallback")
                        tc = TextClip(
                            font="C:/Windows/Fonts/impact.ttf",
                            text=txt, font_size=font_size_scaled,
                            color=f"rgb{hl_text_rgb}",
                            bg_color=f"rgb{hl_bg_rgb}",
                            stroke_width=0, margin=(24, 12),
                            duration=dur, transparent=False,
                        )

                tc_w, tc_h = tc.size
                VPAD = max(40, int(H * 0.03))

                if position == "top":
                    y = VPAD
                elif position == "upper_center":
                    y = int(H * 0.22)
                elif position == "center":
                    y = (H - tc_h) // 2
                elif position == "lower_center":
                    y = int(H * 0.65)
                else:  # bottom
                    y = H - tc_h - VPAD

                y = max(VPAD, min(y, H - tc_h - VPAD))
                x = max(0, (W - tc_w) // 2)

                tc = tc.with_position((x, y)).with_start(start)
                subtitle_clips.append(tc)

            print(f"[1/4] ✓ {len(subtitle_clips)} subtitle clips built")
            jobs[job_id]["progress"] = 35

            # ── Step 2: Logo overlay ───────────────────────
            logo_clip = None
            logo_path = options["logoPath"].strip()
            if logo_path and os.path.exists(logo_path):
                print(f"\n[2/4] Adding logo overlay...")
                logo_size = options["logoSize"]
                logo_pos  = options["logoPosition"]
                PAD = max(60, int(H * 0.050))

                logo   = ImageClip(logo_path, duration=total_dur)
                lw, lh = logo.size
                ratio  = logo_size / max(lw, lh)
                new_w  = int(lw * ratio)
                logo   = logo.resized(width=new_w)

                actual_w, actual_h = logo.size
                pos_map = {
                    "topleft":     (PAD,                   PAD),
                    "topright":    (W - actual_w - PAD,    PAD),
                    "bottomleft":  (PAD,                   H - actual_h - PAD),
                    "bottomright": (W - actual_w - PAD,    H - actual_h - PAD),
                }
                px, py    = pos_map.get(logo_pos, (PAD, PAD))
                px        = max(0, min(px, W - actual_w))
                py        = max(0, min(py, H - actual_h))
                logo_clip = logo.with_position((px, py))
                print(f"[2/4] ✓ Logo placed at ({px},{py})")
            else:
                print(f"\n[2/4] No logo — skipping")

            jobs[job_id]["progress"] = 50

            # ── Step 3: Composite video ────────────────────
            print(f"\n[3/4] Compositing video...")
            all_clips = [video] + subtitle_clips
            if logo_clip:
                all_clips.append(logo_clip)
            final_video = CompositeVideoClip(all_clips)
            print(f"[3/4] ✓ Composite done ({len(all_clips)} layers)")

            # ── Step 4: Background music ───────────────────
            music_path = options["musicPath"].strip()
            if music_path and os.path.exists(music_path):
                print(f"\n[3.5/4] Adding background music...")
                music_vol = options["musicVolume"]
                music     = AudioFileClip(music_path)

                if music.duration < total_dur:
                    loops = int(total_dur / music.duration) + 1
                    from moviepy import concatenate_audioclips
                    music = concatenate_audioclips([music] * loops)

                music = music.subclipped(0, total_dur)

                try:
                    from moviepy.audio.fx import MultiplyVolume
                    music = music.with_effects([MultiplyVolume(music_vol)])
                except Exception as e:
                    print(f"[WARN] Volume scaling failed: {e}")

                original_audio = video.audio
                if original_audio:
                    mixed = CompositeAudioClip([original_audio, music])
                else:
                    mixed = music

                final_video = final_video.with_audio(mixed)
                print(f"[3.5/4] ✓ Music mixed")
            else:
                print(f"\n[3.5/4] No background music — skipping")

            jobs[job_id]["progress"] = 70
            jobs[job_id]["status"]   = "exporting"

            # ── Step 5: Export ─────────────────────────────
            out_name = f"{job_id}_final.mp4"
            out_path = os.path.join(OUTPUT_FOLDER, out_name)

            print(f"\n[4/4] Exporting → {out_path}")

            last_printed = [0]

            class ExportLogger(proglog.ProgressBarLogger):
                def callback(self, **changes):
                    for key, value in changes.items():
                        if key == "index":
                            bars = self.bars
                            if "t" in bars:
                                total = bars["t"].get("total", 1) or 1
                                pct = int((value / total) * 100)
                                job_pct = 70 + int(pct * 0.29)
                                jobs[job_id]["progress"] = min(job_pct, 99)
                                milestone = (pct // 10) * 10
                                if milestone > last_printed[0]:
                                    last_printed[0] = milestone
                                    elapsed = time.time() - jobs[job_id]["start_time"]
                                    print(f"[4/4] Export: {pct}% complete ({elapsed:.0f}s elapsed)")

            export_logger = ExportLogger()

            final_video.write_videofile(
                out_path,
                codec="libx264",
                audio_codec="aac",
                fps=video.fps,
                logger=export_logger,
                threads=4,
                preset="ultrafast",
            )

            video.close()
            final_video.close()

            elapsed_total = time.time() - jobs[job_id]["start_time"]
            print(f"\n[4/4] ✓ Export complete! ({elapsed_total:.1f}s)")

            jobs[job_id]["status"]   = "done"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["output"]   = os.path.abspath(out_path)

            cleanup_job_uploads(job_id)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"\n[ERROR] Render failed: {e}\n{tb}")
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"]  = str(e) + "\n" + tb

    thread = threading.Thread(target=do_render)
    thread.daemon = True
    thread.start()
    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    job      = jobs[job_id]
    elapsed  = time.time() - job.get("start_time", time.time())
    progress = job.get("progress", 0)
    eta = None
    if progress > 5:
        eta = max(0, int(elapsed / (progress / 100) - elapsed))
    return jsonify({
        "status":   job["status"],
        "progress": progress,
        "eta":      eta,
        "chunks":   job.get("chunks", []),
        "output":   job.get("output"),
        "error":    job.get("error"),
        "phase":    job.get("phase", "transcribe"),
    })


@app.route("/download/<job_id>", methods=["GET"])
def download(job_id):
    if job_id not in jobs or jobs[job_id]["status"] != "done":
        return jsonify({"error": "File not ready"}), 404
    return send_file(jobs[job_id]["output"], as_attachment=True, download_name="final_reel.mp4")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, port=int(os.environ.get("PORT", 5000)))



























