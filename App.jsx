
///////////////////////////////////////////----------ORIGINAL----------/////////////////////////////////////////////




import { useState, useRef, useEffect, useCallback } from "react";
import "./fonts.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:5000";

const FONTS = [ "Arial-Black", "OpenSans-Regular", "Carlito-Bold","ComicNeue-Regular", "bahnschrift", "BarlowCondensed-Bold", "Anton", "BarlowCondensed-Black","LilitaOne-Regular"];
const STYLES = [
  { id: "highlight", label: "Highlight Box", desc: "Colored box behind text" },
  { id: "outline",   label: "Bold Outline",  desc: "White text with black stroke" },
  { id: "plain",     label: "Plain Text",    desc: "Clean minimal text" },
  
];


const TRANSITIONS = [
  { id: "cut",         label: "Cut (none)" },
  { id: "fade",        label: "Fade" },
  { id: "fadeblack",   label: "Fade to Black" },
  { id: "fadewhite",   label: "Fade to White" },
  { id: "dissolve",    label: "Dissolve" },
  { id: "wipeleft",    label: "Wipe Left" },
  { id: "wiperight",   label: "Wipe Right" },
  { id: "wipeup",      label: "Wipe Up" },
  { id: "wipedown",    label: "Wipe Down" },
  { id: "slideleft",   label: "Slide Left" },
  { id: "slideright",  label: "Slide Right" },
  { id: "slideup",     label: "Slide Up" },
  { id: "slidedown",   label: "Slide Down" },
  { id: "circlecrop",  label: "Circle Crop" },
  { id: "circleopen",  label: "Circle Open" },
  { id: "circleclose", label: "Circle Close" },
  { id: "zoomin",      label: "Zoom In" },
  { id: "pixelize",    label: "Pixelize" },
  { id: "hblur",       label: "Horizontal Blur" },
];
const POSITIONS = [
  { id: "top",          label: "Top",       icon: "▲", previewStyle: { top: 8 } },
  { id: "upper_center", label: "Upper Mid", icon: "△", previewStyle: { top: "28%" } },
  { id: "center",       label: "Center",    icon: "●", previewStyle: { top: "50%", transform: "translateY(-50%)" } },
  { id: "lower_center", label: "Lower Mid", icon: "▽", previewStyle: { top: "68%" } },
  { id: "bottom",       label: "Bottom",    icon: "▼", previewStyle: { bottom: 8 } },
];
const LOGO_POSITIONS = [
  { id: "topleft",     label: "Top Left" },
  { id: "topright",    label: "Top Right" },
  { id: "bottomleft",  label: "Bottom Left" },
  { id: "bottomright", label: "Bottom Right" },
];
const STATUS_LABELS = {
  cropping:              "Cropping video segment...",
  merging:               "Merging clips...",
  extracting_audio:      "Extracting audio...",
  transcribing:          "Whisper AI transcribing...",
  awaiting_confirmation: "Ready for review!",
  rendering:             "Rendering subtitles...",
  exporting:             "Exporting final video...",
  done:                  "Complete!",
  error:                 "Error occurred",
};

// ─── Mode 1 fixed size options ─────────────────────────────────────────────
const MODE1_FONT_SIZES = [68, 72];
const MODE1_LOGO_SIZES = [160, 180];

// ─── NEW: quick-pick swatches shown for per-word emphasis coloring ─────────
const WORD_COLOR_PRESETS = ["#FF3B30", "#FFD60A", "#34C759", "#0A84FF", "#FF2D55", "#FFFFFF"];


// ─── Reusable: fixed/toggle size selector (replaces free sliders) ─────────
function SizeToggle({ label, value, options, onChange, unit = "px" }) {
  const isFixed = options.length === 1;
  return (
    <div style={S.section}>
      <label style={S.label}>
        {label} {isFixed && <span style={S.optional}>(fixed)</span>}
      </label>
      {isFixed ? (
        <div style={S.fixedBadge}>{options[0]}{unit}</div>
      ) : (
        <div style={S.posBtns}>
          {options.map(opt => (
            <button key={opt}
              style={{ ...S.sizeBtn, ...(value === opt ? S.sizeBtnOn : {}) }}
              onClick={() => onChange(opt)}>
              {opt}{unit}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function TransitionPicker({ value, onChange }) {
  return (
    <div style={S.transitionRow}>
      <div style={S.transitionLine} />
      <select
        style={S.transitionSelect}
        value={value}
        onChange={e => onChange(e.target.value)}
      >
        {TRANSITIONS.map(t => (
          <option key={t.id} value={t.id}>{t.label}</option>
        ))}
      </select>
      <div style={S.transitionLine} />
    </div>
  );
}

// ─── Reusable: browse-from-device upload field ─────────────────────────────
function FileUploadField({ label, accept, hint, optional, fileName, uploading, onUpload, icon = "📄" }) {
  return (
    <div style={S.section}>
      <label style={S.label}>{label} {optional && <span style={S.optional}>{optional}</span>}</label>
      <label style={S.uploadBox}>
        <input type="file" accept={accept} style={{ display: "none" }} onChange={onUpload} />
        {uploading
          ? <span style={{ color: "#f5a623", fontSize: 12 }}>Uploading...</span>
          : fileName
            ? <span style={{ color: "#22c55e", fontSize: 12 }}>{icon} {fileName}</span>
            : <span style={{ color: "#555", fontSize: 12 }}>Click to browse & upload</span>}
      </label>
      {hint && <p style={S.hint}>{hint}</p>}
    </div>
  );
}

// ─── NEW: per-word color chip row — shown under each subtitle card ─────────
// Lets the user tint an individual word (e.g. make "starving" red) without
// affecting the rest of the card's text color / highlight box.
function WordColorEditor({ text, wordColors, onSetColor, onClearColor }) {
  const words = text.split(" ").filter(Boolean);
  if (words.length === 0) return null;

  return (
    <div style={S.wordColorRow}>
      {words.map((word, wi) => {
        const activeColor = wordColors?.[wi];
        return (
          <div key={wi} style={{ ...S.wordChip, ...(activeColor ? { borderColor: activeColor } : {}) }}>
            <span style={{ color: activeColor || "#aaa", fontWeight: activeColor ? 800 : 500, fontSize: 12 }}>
              {word}
            </span>
            <div style={S.wordChipControls}>
              {WORD_COLOR_PRESETS.map(c => (
                <div
                  key={c}
                  onClick={() => onSetColor(wi, c)}
                  title={`Color "${word}" ${c}`}
                  style={{
                    ...S.wordDot,
                    background: c,
                    outline: activeColor === c ? "2px solid #fff" : "1px solid #333",
                  }}
                />
              ))}
              <input
                type="color"
                value={activeColor || "#ffffff"}
                onChange={e => onSetColor(wi, e.target.value)}
                style={S.wordColorInput}
                title="Custom color"
              />
              {activeColor && (
                <button style={S.wordClearBtn} onClick={() => onClearColor(wi)} title="Reset to default color">×</button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Shared style controls component ──────────────────────────────────────────
function StylePanel({
  style, setStyle, font, setFont, fontSize, setFontSize,
  fontSizeOptions, logoSizeOptions,
  textColor, setTextColor, highlightColor, setHighlightColor,
  hlTextColor, setHlTextColor, position, setPosition,
  logoFileName, logoUploading, onLogoUpload,
  logoPosition, setLogoPosition, logoSize, setLogoSize,
  musicPath, setMusicPath, musicVolume, setMusicVolume,
  onMusicUpload, musicFileName,
}) {
  const previewFontSize = Math.max(10, Math.min(fontSize * 0.28, 28));
  const currentPosition = POSITIONS.find(p => p.id === position);
  const previewTextStyle = {
    fontFamily: font, fontSize: previewFontSize, fontWeight: 900,
    letterSpacing: 2, whiteSpace: "nowrap",
    color:      style === "highlight" ? hlTextColor : textColor,
    background: style === "highlight" ? highlightColor : "transparent",
    padding:    style === "highlight" ? "8px 16px" : "0",
    borderRadius: style === "highlight" ? 12 : 3,
    display: "inline-flex", alignItems: "center",
    textShadow: style === "outline"
      ? "-2px -2px 0 #000,2px -2px 0 #000,-2px 2px 0 #000,2px 2px 0 #000"
      : "none",
  };
  const styleCardPreview = (st) => {
    if (st.id === "highlight") return <span style={{ background: highlightColor, color: hlTextColor, padding: "2px 8px", borderRadius: 8, fontWeight: 900, fontSize: 12 }}>REELS</span>;
    if (st.id === "outline")   return <span style={{ color: textColor, fontWeight: 900, fontSize: 12, textShadow: "-1px -1px 0 #000,1px -1px 0 #000,-1px 1px 0 #000,1px 1px 0 #000" }}>REELS</span>;
    return <span style={{ color: textColor, fontWeight: 900, fontSize: 12 }}>REELS</span>;
  };

  return (
    <>
      {/* SUBTITLE STYLE */}
      <div style={S.sectionTitle}>SUBTITLE STYLE</div>
      <div style={S.section}>
        <label style={S.label}>Style</label>
        <div style={S.styleCards}>
          {STYLES.map(st => (
            <div key={st.id} style={{ ...S.styleCard, ...(style === st.id ? S.styleCardActive : {}) }}
              onClick={() => setStyle(st.id)}>
              <div style={S.stylePreview}>{styleCardPreview(st)}</div>
              <p style={S.styleName}>{st.label}</p>
              <p style={S.styleDesc}>{st.desc}</p>
            </div>
          ))}
        </div>
      </div>

      <div style={S.grid2}>
        <div style={S.section}>
          <label style={S.label}>Font</label>
          <select style={S.select} value={font} onChange={e => setFont(e.target.value)}>
            {FONTS.map(f => <option key={f}>{f}</option>)}
          </select>
        </div>

        <SizeToggle label="Font Size" value={fontSize} options={fontSizeOptions} onChange={setFontSize} />

        {/* Text color — for outline/plain only */}
        {style !== "highlight" && (
          <div style={S.section}>
            <label style={S.label}>Text Color <span style={S.optional}>(default — override per word below in Review step)</span></label>
            <div style={S.colorRow}>
              <input type="color" value={textColor} onChange={e => setTextColor(e.target.value)} style={S.colorPick} />
              <span style={S.colorHex}>{textColor.toUpperCase()}</span>
              <div style={S.presets}>
                {["#FFFFFF","#FFFF00","#000000","#FF4444","#44FFAA","#FF8800"].map(c => (
                  <div key={c} onClick={() => setTextColor(c)}
                    style={{ ...S.dot, background: c, outline: textColor === c ? "2px solid #fff" : "2px solid #333" }} />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Highlight box color */}
        {style === "highlight" && (
          <div style={S.section}>
            <label style={S.label}>Box Color</label>
            <div style={S.colorRow}>
              <input type="color" value={highlightColor} onChange={e => setHighlightColor(e.target.value)} style={S.colorPick} />
              <span style={S.colorHex}>{highlightColor.toUpperCase()}</span>
              <div style={S.presets}>
                {["#F5A623","#FF3B30","#34C759","#007AFF","#FF2D55","#FFFFFF"].map(c => (
                  <div key={c} onClick={() => setHighlightColor(c)}
                    style={{ ...S.dot, background: c, outline: highlightColor === c ? "2px solid #fff" : "2px solid #333" }} />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Highlight text color */}
        {style === "highlight" && (
          <div style={S.section}>
            <label style={S.label}>Text Color <span style={S.optional}>(inside box — override per word below in Review step)</span></label>
            <div style={S.colorRow}>
              <input type="color" value={hlTextColor} onChange={e => setHlTextColor(e.target.value)} style={S.colorPick} />
              <span style={S.colorHex}>{hlTextColor.toUpperCase()}</span>
              <div style={S.presets}>
                {["#000000","#FFFFFF","#1a1a1a","#FF3B30","#007AFF","#34C759"].map(c => (
                  <div key={c} onClick={() => setHlTextColor(c)}
                    style={{ ...S.dot, background: c, outline: hlTextColor === c ? "2px solid #fff" : "2px solid #333" }} />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Position */}
        <div style={{ ...S.section, gridColumn: "1 / -1" }}>
          <label style={S.label}>Subtitle Position</label>
          <div style={S.posBtns}>
            {POSITIONS.map(p => (
              <button key={p.id}
                style={{ ...S.posBtn, ...(position === p.id ? S.posBtnOn : {}) }}
                onClick={() => setPosition(p.id)}>
                <span style={{ fontSize: 14 }}>{p.icon}</span>
                <span style={{ fontSize: 9, textAlign: "center", lineHeight: 1.2 }}>{p.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Live Preview */}
      <div style={S.section}>
        <label style={S.label}>Live Preview</label>
        <div style={S.previewScreen}>
          <div style={S.previewBars}>
            {[80,55,70,40].map((w,i) => <div key={i} style={{ ...S.previewBar, width: `${w}%` }} />)}
          </div>
          {POSITIONS.map(p => (
            <div key={p.id} style={{
              position: "absolute", left: 0, right: 0,
              display: "flex", justifyContent: "center",
              ...p.previewStyle,
              opacity: position === p.id ? 1 : 0,
              transition: "opacity 0.2s",
            }}>
              <span style={previewTextStyle}>REELS STYLE</span>
            </div>
          ))}
          <div style={{ position: "absolute", bottom: 6, right: 8, fontSize: 9, color: "#f5a623", letterSpacing: "0.1em" }}>
            {currentPosition?.label?.toUpperCase()}
          </div>
        </div>
      </div>

      <div style={S.divider} />

      {/* LOGO */}
      <div style={S.sectionTitle}>LOGO OVERLAY</div>
      <div style={S.grid2}>
        <FileUploadField
          label="Logo File"
          accept="image/*"
          optional="(PNG recommended)"
          fileName={logoFileName}
          uploading={logoUploading}
          onUpload={onLogoUpload}
          icon="🖼️"
          hint="Leave empty to skip logo"
        />

        <SizeToggle label="Logo Size" value={logoSize} options={logoSizeOptions} onChange={setLogoSize} />

        <div style={S.section}>
          <label style={S.label}>Logo Position</label>
          <div style={S.logoGrid}>
            {LOGO_POSITIONS.map(p => (
              <button key={p.id}
                style={{ ...S.logoBtn, ...(logoPosition === p.id ? S.logoBtnOn : {}) }}
                onClick={() => setLogoPosition(p.id)}>{p.label}</button>
            ))}
          </div>
        </div>
      </div>

      <div style={S.divider} />

      {/* MUSIC */}
      <div style={S.sectionTitle}>BACKGROUND MUSIC</div>
      <div style={S.grid2}>
        <div style={S.section}>
          <label style={S.label}>Music File <span style={S.optional}>(MP3 / WAV)</span></label>
          <label style={S.uploadBox}>
            <input type="file" accept="audio/*" style={{ display: "none" }}
              onChange={onMusicUpload} />
            {musicFileName
              ? <span style={{ color: "#f5a623", fontSize: 12 }}>🎵 {musicFileName}</span>
              : <span style={{ color: "#555", fontSize: 12 }}>Click to upload music file</span>}
          </label>
          <p style={S.hint}>Original audio stays. Music mixed on top.</p>
        </div>
        <div style={S.section}>
          <label style={S.label}>Music Volume <span style={S.val}>{musicVolume}%</span></label>
          <input type="range" min={0} max={100} step={5}
            value={musicVolume} onChange={e => setMusicVolume(+e.target.value)} style={S.range} />
          <div style={S.ticks}><span>0%</span><span>50%</span><span>100%</span></div>
        </div>
      </div>
    </>
  );
}

// ─── Clip drop zone + drag-reorder list ───────────────────────────────────────
function ClipList({ clips, onAdd, onReorder, onRemove, onUpdateTransition, uploading }) {
  const dragItem   = useRef(null);
  const dragOverItem = useRef(null);

  const handleDragStart = (i) => { dragItem.current = i; };
  const handleDragEnter = (i) => { dragOverItem.current = i; };
  const handleDragEnd   = () => {
    if (dragItem.current === null || dragOverItem.current === null) return;
    if (dragItem.current === dragOverItem.current) return;
    const reordered = [...clips];
    const dragged   = reordered.splice(dragItem.current, 1)[0];
    reordered.splice(dragOverItem.current, 0, dragged);
    onReorder(reordered);
    dragItem.current = null;
    dragOverItem.current = null;
  };


  const handleFileDrop = (e) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith("video/"));
    files.forEach(f => onAdd(f));
  };

  return (
    <div>
      {/* Drop zone */}
      <label
        onDragOver={e => e.preventDefault()}
        onDrop={handleFileDrop}
        style={S.dropZone}
      >
        <input type="file" accept="video/*" multiple style={{ display: "none" }}
          onChange={e => Array.from(e.target.files).forEach(f => onAdd(f))} />
        <div style={{ fontSize: 28, marginBottom: 8 }}>📁</div>
        <p style={{ margin: 0, fontSize: 13, color: "#888" }}>
          Drag & drop video clips here, or <span style={{ color: "#f5a623" }}>browse</span>
        </p>
        <p style={{ margin: "4px 0 0", fontSize: 11, color: "#444" }}>MP4, MOV, AVI supported</p>
        {uploading && <p style={{ color: "#f5a623", fontSize: 12, marginTop: 8 }}>Uploading...</p>}
      </label>

      {/* Clip list with drag reorder */}
      {clips.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <p style={{ fontSize: 11, color: "#555", margin: "0 0 8px", letterSpacing: "0.1em" }}>
            DRAG TO REORDER — {clips.length} CLIP{clips.length > 1 ? "S" : ""}
          </p>
          {clips.map((clip, i) => (
            <div key={clip.clip_id}>
              <div
                draggable
                onDragStart={() => handleDragStart(i)}
                onDragEnter={() => handleDragEnter(i)}
                onDragEnd={handleDragEnd}
                style={S.clipRow}
              >
                <span style={S.clipHandle}>⠿</span>
                <span style={S.clipNum}>{i + 1}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={S.clipName}>{clip.filename}</p>
                  <p style={S.clipDur}>{clip.duration?.toFixed(1)}s</p>
                </div>
                <button style={S.clipRemove} onClick={() => onRemove(i)}>✕</button>
              </div>
              {i < clips.length - 1 && (
                <TransitionPicker
                  value={clip.transitionAfter || "cut"}
                  onChange={val => onUpdateTransition(i, val)}
                />
              )}
            </div>
          ))}
          <p style={{ fontSize: 11, color: "#444", marginTop: 8 }}>
            Total: {clips.reduce((a, c) => a + (c.duration || 0), 0).toFixed(1)}s
          </p>
        </div>
      )}
    </div>
  );
}

function SegmentList({ segments, onAdd, onReorder, onRemove, onUpdate, onUpdateTransition }) {
  const dragItem = useRef(null);
  const dragOverItem = useRef(null);

  const handleDragStart = (i) => { dragItem.current = i; };
  const handleDragEnter = (i) => { dragOverItem.current = i; };
  const handleDragEnd = () => {
    if (dragItem.current === null || dragOverItem.current === null) return;
    if (dragItem.current === dragOverItem.current) return;
    const reordered = [...segments];
    const dragged = reordered.splice(dragItem.current, 1)[0];
    reordered.splice(dragOverItem.current, 0, dragged);
    onReorder(reordered);
    dragItem.current = null;
    dragOverItem.current = null;
  };

  return (
    <div>
      <p style={{ fontSize: 11, color: "#555", margin: "0 0 8px", letterSpacing: "0.1em" }}>
        DRAG TO REORDER — {segments.length} SEGMENT{segments.length > 1 ? "S" : ""}
      </p>
      {segments.map((seg, i) => (
        <div key={seg.id}>
          <div draggable
            onDragStart={() => handleDragStart(i)}
            onDragEnter={() => handleDragEnter(i)}
            onDragEnd={handleDragEnd}
            style={S.clipRow}>
            <span style={S.clipHandle}>⠿</span>
            <span style={S.clipNum}>{i + 1}</span>
            <input style={S.timeInput} placeholder="Start e.g. 3:01"
              value={seg.startTime}
              onChange={e => onUpdate(i, "startTime", e.target.value)} />
            <input style={S.timeInput} placeholder="End e.g. 3:44"
              value={seg.endTime}
              onChange={e => onUpdate(i, "endTime", e.target.value)} />
            <button style={S.clipRemove} onClick={() => onRemove(i)}>✕</button>
          </div>
          {i < segments.length - 1 && (
            <TransitionPicker
              value={seg.transitionAfter || "cut"}
              onChange={val => onUpdateTransition(i, val)}
            />
          )}
        </div>
      ))}
      <button style={{ ...S.backBtn, marginTop: 10, width: "auto" }} onClick={onAdd}>
        + Add Timestamp
      </button>
    </div>
  );
}

// ─── Processing screen (shared by all modes) ──────────────────────────────────
function ProcessingScreen({ jobPhase, jobStatus, progress, errorMsg, onBack }) {
  return (
    <div style={S.card}>
      <label style={S.stepTag}>PROCESSING</label>
      <h2 style={S.cardH}>
        {jobPhase === "transcribe" ? "Preparing Your Video..." : "Generating Your Reel..."}
      </h2>
      <div style={S.progTrack}>
        <div style={{ ...S.progFill, width: `${progress}%` }}>
          <div style={S.progShine} />
        </div>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "#f5a623" }}>{progress}%</span>
        <span style={{ fontSize: 12, color: "#555" }}>{STATUS_LABELS[jobStatus] || "Working..."}</span>
      </div>

      {jobPhase === "transcribe" && (
        <div style={S.stepRow}>
          {[
            { key: "merging",          label: "Merge" },
            { key: "extracting_audio", label: "Audio" },
            { key: "transcribing",     label: "Transcribe" },
          ].map((st, i) => {
            const order = ["merging","cropping","extracting_audio","transcribing","awaiting_confirmation"];
            const ci    = order.indexOf(jobStatus);
            const si    = order.indexOf(st.key);
            return (
              <div key={st.key} style={S.stepCol}>
                <div style={{ ...S.stepBubble, ...(ci > si ? S.bubbleDone : ci === si ? S.bubbleActive : {}) }}>
                  {ci > si ? "✓" : i + 1}
                </div>
                <span style={{ ...S.stepLbl, opacity: ci >= si ? 1 : 0.3 }}>{st.label}</span>
              </div>
            );
          })}
        </div>
      )}

      {jobPhase === "render" && (
        <div style={S.stepRow}>
          {[{ key: "rendering", label: "Render" }, { key: "exporting", label: "Export" }, { key: "done", label: "Done" }].map((st, i) => {
            const order = ["rendering","exporting","done"];
            const ci    = order.indexOf(jobStatus);
            const si    = order.indexOf(st.key);
            return (
              <div key={st.key} style={S.stepCol}>
                <div style={{ ...S.stepBubble, ...(ci > si ? S.bubbleDone : ci === si ? S.bubbleActive : {}) }}>
                  {ci > si ? "✓" : i + 1}
                </div>
                <span style={{ ...S.stepLbl, opacity: ci >= si ? 1 : 0.3 }}>{st.label}</span>
              </div>
            );
          })}
        </div>
      )}

      {errorMsg && (
        <div style={S.modalErr}>
          ⚠ {errorMsg}
          <button style={S.closeBtn} onClick={onBack}>Back</button>
        </div>
      )}
    </div>
  );
}

// ─── Done popup (shared) — Download Video + Process Another Video ────────────
function DonePopup({ outputPath, jobId, onReset }) {
  return (
    <div style={S.overlay}>
      <div style={{ ...S.modal, borderColor: "#22c55e55" }}>
        <div style={{ ...S.modalGlow, background: "radial-gradient(circle, #22c55e22 0%, transparent 70%)" }} />
        <div style={S.checkRing}>✓</div>
        <h3 style={{ ...S.modalTitle, color: "#22c55e" }}>Reel Ready!</h3>
        <p style={S.modalSub}>Your video has been processed successfully</p>
        <div style={S.outBox}>
          <span style={S.outLabel}>SAVED TO</span>
          <p style={S.outPath}>{outputPath}</p>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <a
            style={{ ...S.primaryBtn, flex: 1, textDecoration: "none", textAlign: "center", boxSizing: "border-box" }}
            href={`${API}/download/${jobId}`}
            download
          >
            ⬇ Download Video
          </a>
          <button style={{ ...S.backBtn, flex: 1 }} onClick={onReset}>Process Another Video</button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN APP
// ─────────────────────────────────────────────────────────────────────────────
export default function App() {
  // ── App mode: "landing" | "mode1" | "mode2" ──
  const [appMode, setAppMode] = useState("landing");

  // ── Shared job state ──
  const [jobId,      setJobId]      = useState(null);
  const [jobPhase,   setJobPhase]   = useState("transcribe");
  const [jobStatus,  setJobStatus]  = useState(null);
  const [progress,   setProgress]   = useState(0);
  const [outputPath, setOutputPath] = useState("");
  const [errorMsg,   setErrorMsg]   = useState("");
  const [showDone,   setShowDone]   = useState(false);
  const [processing, setProcessing] = useState(false);
  const [chunks,     setChunks]     = useState([]);

  // ── Mode 1 state ──
  const [videoServerPath, setVideoServerPath] = useState("");
  const [videoFileName,   setVideoFileName]   = useState("");
  const [videoUploading,  setVideoUploading]  = useState(false);
  const [videoError,      setVideoError]      = useState("");
// Mode 1 segments — add transitionAfter default
const [segments, setSegments] = useState([
  { id: crypto.randomUUID(), startTime: "0:00", endTime: "", transitionAfter: "cut" }
]);
  const [wordsPerCard, setWordsPerCard] = useState(2);

  // ── Mode 2 clip state (Audio Transcription only) ──
  const [clips,          setClips]          = useState([]);
  const [clipUploading,  setClipUploading]  = useState(false);
  const [audioFile,      setAudioFile]      = useState(null);   // { path, filename }
  const [audioUploading, setAudioUploading] = useState(false);
  const [mode2wpc,       setMode2wpc]       = useState(2);

  // ── Shared style state ──
  const [style,          setStyle]          = useState("highlight");
  const [font,           setFont]           = useState("Impact");
  const [fontSize,       setFontSize]       = useState(72);
  const [textColor,      setTextColor]      = useState("#FFFFFF");
  const [highlightColor, setHighlightColor] = useState("#F5A623");
  const [hlTextColor,    setHlTextColor]    = useState("#000000");
  const [position,       setPosition]       = useState("bottom");
  const [logoServerPath, setLogoServerPath] = useState("");
  const [logoFileName,   setLogoFileName]   = useState("");
  const [logoUploading,  setLogoUploading]  = useState(false);
  const [logoPosition,   setLogoPosition]   = useState("topright");
  const [logoSize,       setLogoSize]       = useState(160);
  const [musicServerPath, setMusicServerPath] = useState("");
  const [musicFileName,   setMusicFileName]   = useState("");
  const [musicVolume,    setMusicVolume]    = useState(30);

  // ── Review step ──
  const [showReview, setShowReview] = useState(false);

  const pollRef  = useRef(null);
  const jobIdRef = useRef(null);
  useEffect(() => { jobIdRef.current = jobId; }, [jobId]);
 
  // ── Keep font/logo size within the allowed set for the active mode/style ──
 // NEW
useEffect(() => {
  if (appMode === "mode1" || appMode === "mode2") {
    setFontSize(prev => (MODE1_FONT_SIZES.includes(prev) ? prev : MODE1_FONT_SIZES[1]));
    setLogoSize(prev => (MODE1_LOGO_SIZES.includes(prev) ? prev : MODE1_LOGO_SIZES[0]));
  }
}, [appMode]);

  // ── Polling ──────────────────────────────────────────────
  const startPolling = (phase) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const currentJobId = jobIdRef.current;
      if (!currentJobId) return;
      try {
        const res  = await fetch(`${API}/status/${currentJobId}`);
        const data = await res.json();
        setJobStatus(data.status);
        setProgress(data.progress || 0);

        if (phase === "transcribe") {
          if (data.status === "awaiting_confirmation") {
            clearInterval(pollRef.current);
            // NEW: attach an empty wordColors map to each chunk so the
            // per-word color editor always has something to read/write.
            setChunks((data.chunks || []).map(c => ({ ...c, wordColors: c.wordColors || {} })));
            setProcessing(false);
            setShowReview(true);
          } else if (data.status === "error") {
            clearInterval(pollRef.current);
            setErrorMsg(data.error || "Failed.");
            setProcessing(false);
          }
        } else {
          if (data.status === "done") {
            clearInterval(pollRef.current);
            setOutputPath(data.output || "");
            setProgress(100);
            setShowDone(true);
            setProcessing(false);
          } else if (data.status === "error") {
            clearInterval(pollRef.current);
            setErrorMsg(data.error || "Render failed.");
            setProcessing(false);
          }
        }
      } catch {
        clearInterval(pollRef.current);
        setErrorMsg("Lost connection to server.");
        setProcessing(false);
      }
    }, 1500);
  };

  // ── Handlers ─────────────────────────────────────────────

  // Mode 1 video upload (browse from device)
  const handleVideoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setVideoUploading(true);
    setVideoError(""); setErrorMsg("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res  = await fetch(`${API}/upload-video`, { method: "POST", body: form });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setVideoServerPath(data.path);
      setVideoFileName(data.filename);
    } catch (err) {
      setErrorMsg(`Video upload failed: ${err.message}`);
    } finally {
      setVideoUploading(false);
    }
  };

  // Logo upload (browse from device) — shared by Mode 1 & Mode 2
  const handleLogoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLogoUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res  = await fetch(`${API}/upload-logo`, { method: "POST", body: form });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setLogoServerPath(data.path);
      setLogoFileName(data.filename);
    } catch (err) {
      setErrorMsg(`Logo upload failed: ${err.message}`);
    } finally {
      setLogoUploading(false);
    }
  };

  // Mode 1 transcribe
  const handleMode1Transcribe = async () => {
    if (!videoServerPath) { setVideoError("Please upload a video file."); return; }
    setVideoError(""); setErrorMsg("");
    setProcessing(true);
    setJobPhase("transcribe");
    setJobStatus("cropping"); setProgress(5);
    try {
      const res  = await fetch(`${API}/transcribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // handleMode1Transcribe — inside the fetch body:
body: JSON.stringify({
  video_path: videoServerPath,
  segments: segments.map(s => ({ startTime: s.startTime, endTime: s.endTime })),
  transitions: segments.slice(0, -1).map(s => s.transitionAfter || "cut"),
  wordsPerCard,
}),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setJobId(data.job_id);
      jobIdRef.current = data.job_id;
      startPolling("transcribe");
    } catch (err) {
      setErrorMsg(err.message);
      setProcessing(false);
    }
  };

  // Mode 2 clip upload
// Mode 2 — tag newly uploaded clips with a default transition
const handleClipAdd = async (file) => {
  setClipUploading(true);
  try {
    const form = new FormData();
    form.append("file", file);
    const res  = await fetch(`${API}/upload-clip`, { method: "POST", body: form });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    setClips(prev => [...prev, { ...data, transitionAfter: "cut" }]);
  } catch (err) {
    setErrorMsg(`Upload failed: ${err.message}`);
  } finally {
    setClipUploading(false);
  }
};

  // Mode 2 audio upload
  const handleAudioUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setAudioUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res  = await fetch(`${API}/upload-audio`, { method: "POST", body: form });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setAudioFile({ path: data.path, filename: data.filename, duration: data.duration });
    } catch (err) {
      setErrorMsg(`Audio upload failed: ${err.message}`);
    } finally {
      setAudioUploading(false);
    }
  };

  // Music upload (shared)
  const handleMusicUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const form = new FormData();
      form.append("file", file);
      const res  = await fetch(`${API}/upload-music`, { method: "POST", body: form });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setMusicServerPath(data.path);
      setMusicFileName(data.filename);
    } catch (err) {
      setErrorMsg(`Music upload failed: ${err.message}`);
    }
  };

  // Mode 2 — kick off merge-clips job (Audio Transcription only)
  const handleMode2Start = async () => {
    if (clips.length === 0) { setErrorMsg("Please add at least one clip."); return; }
    if (!audioFile) { setErrorMsg("Please upload an audio file to transcribe."); return; }

    setErrorMsg("");
    setProcessing(true);
    setJobPhase("transcribe");
    setJobStatus("merging"); setProgress(5);

    // handleMode2Start — the body object:
    const body = {
      clip_paths:   clips.map(c => c.path),
      transitions:  clips.slice(0, -1).map(c => c.transitionAfter || "cut"),
      subtitleMode: "transcribe",
      wordsPerCard: mode2wpc,
      audio_path:   audioFile?.path || "",
    };

    try {
      const res  = await fetch(`${API}/merge-clips`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setJobId(data.job_id);
      jobIdRef.current = data.job_id;
      startPolling("transcribe");
    } catch (err) {
      setErrorMsg(err.message);
      setProcessing(false);
    }
  };

  // Render (shared)
  const handleRender = async () => {
    setErrorMsg("");
    setShowReview(false);
    setProcessing(true);
    setJobPhase("render");
    setJobStatus("rendering"); setProgress(0);
    try {
      const res = await fetch(`${API}/render`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: jobId, chunks,
          font, fontSize, textColor,
          highlightColor, highlightTextColor: hlTextColor,
          position, style,
          logoPath: logoServerPath, logoPosition, logoSize,
          musicPath:   musicServerPath,
          musicVolume: musicVolume / 100,
        }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      startPolling("render");
    } catch (err) {
      setErrorMsg(err.message);
      setShowReview(true);
      setProcessing(false);
    }
  };

  const updateChunk = (i, val) => {
    const updated = [...chunks];
    updated[i] = { ...updated[i], text: val };
    setChunks(updated);
  };

  // NEW: set/clear the color override for one specific word within one chunk
  const setWordColor = (chunkIdx, wordIdx, color) => {
    setChunks(prev => {
      const updated = [...prev];
      const wc = { ...(updated[chunkIdx].wordColors || {}) };
      wc[wordIdx] = color;
      updated[chunkIdx] = { ...updated[chunkIdx], wordColors: wc };
      return updated;
    });
  };

  const clearWordColor = (chunkIdx, wordIdx) => {
    setChunks(prev => {
      const updated = [...prev];
      const wc = { ...(updated[chunkIdx].wordColors || {}) };
      delete wc[wordIdx];
      updated[chunkIdx] = { ...updated[chunkIdx], wordColors: wc };
      return updated;
    });
  };

  const reset = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setAppMode("landing");
    setJobId(null); jobIdRef.current = null;
    setJobStatus(null); setProgress(0);
    setOutputPath(""); setErrorMsg(""); setShowDone(false);
    setProcessing(false); setShowReview(false); setChunks([]);
    setClips([]); setAudioFile(null);
    setMusicServerPath(""); setMusicFileName("");
    setVideoServerPath(""); setVideoFileName(""); setVideoError("");
    setLogoServerPath(""); setLogoFileName("");
    setSegments([{ id: crypto.randomUUID(), startTime: "0:00", endTime: "", transitionAfter: "cut" }]);
  };

  // ── StylePanel props per mode (font/logo size options differ) ──
  const mode1StyleProps = {
    style, setStyle, font, setFont, fontSize, setFontSize,
    fontSizeOptions: MODE1_FONT_SIZES,
    logoSizeOptions: MODE1_LOGO_SIZES,
    textColor, setTextColor, highlightColor, setHighlightColor,
    hlTextColor, setHlTextColor, position, setPosition,
    logoFileName, logoUploading, onLogoUpload: handleLogoUpload,
    logoPosition, setLogoPosition, logoSize, setLogoSize,
    musicPath: musicServerPath, setMusicPath: setMusicServerPath,
    musicVolume, setMusicVolume,
    onMusicUpload: handleMusicUpload, musicFileName,
  };

  //const mode2SizeOpts = TRANSCRIBE_SIZE_MAP[style] || TRANSCRIBE_SIZE_MAP.highlight;
// NEW
const mode2StyleProps = {
  ...mode1StyleProps,
};
  // ─────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────
  return (
    <div style={S.root}>
      <div style={S.noise} />
      <div style={S.glow1} /><div style={S.glow2} />
      <div style={S.page}>

        <header style={S.header}>
          <div style={S.headerInner}>
            <span style={S.reel}>◈</span>
            <div>
              <h1 style={S.title}>ReelSub <span style={S.titleAi}>AI</span></h1>
              <p style={S.subtitle}>AI Reel Editor · Subtitles · Logo · Music</p>
            </div>
          </div>
        </header>

        {/* ══════════════════════════════════════════════════
            LANDING — pick mode
        ══════════════════════════════════════════════════ */}
        {appMode === "landing" && (
          <div>
            <p style={{ color: "#888", marginBottom: 28, fontSize: 14 }}>
              Choose how you want to create your reel:
            </p>
            <div style={S.modeGrid}>

              {/* Mode 1 */}
              <div style={S.modeCard} onClick={() => setAppMode("mode1")}>
                <div style={S.modeIcon}>🎬</div>
                <h2 style={S.modeTitle}>Single Long Video</h2>
                <p style={S.modeDesc}>
                  Upload one long video, set a clip range, and let Whisper AI transcribe
                  it automatically. Review and edit subtitles, then render with your chosen style.
                </p>
                <div style={S.modeFeatures}>
                  <span style={S.feat}>✓ Auto transcription</span>
                  <span style={S.feat}>✓ Crop to exact segment</span>
                  <span style={S.feat}>✓ Edit subtitles</span>
                </div>
                <div style={{ ...S.primaryBtn, marginTop: 20, textAlign: "center" }}>
                  Select →
                </div>
              </div>

              {/* Mode 2 */}
              <div style={S.modeCard} onClick={() => setAppMode("mode2")}>
                <div style={S.modeIcon}>🎞️</div>
                <h2 style={S.modeTitle}>Multiple Clips</h2>
                <p style={S.modeDesc}>
                  Upload multiple video clips, drag to set their order, then upload an
                  audio file — Whisper AI transcribes it and syncs subtitles automatically.
                </p>
                <div style={S.modeFeatures}>
                  <span style={S.feat}>✓ Drag & drop reorder</span>
                  <span style={S.feat}>✓ Auto transcription</span>
                  <span style={S.feat}>✓ Audio replacement</span>
                </div>
                <div style={{ ...S.primaryBtn, marginTop: 20, textAlign: "center" }}>
                  Select →
                </div>
              </div>

            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════
            MODE 1 — single long video
        ══════════════════════════════════════════════════ */}
        {appMode === "mode1" && !processing && !showReview && (
          <div style={S.card}>
            <button style={S.backChip} onClick={() => setAppMode("landing")}>← Back</button>
            <label style={S.stepTag}>MODE 01 — SINGLE VIDEO</label>
            <h2 style={S.cardH}>Video & Clip Settings</h2>
            <p style={S.cardSub}>Upload your video and set the segment timestamps</p>

            <FileUploadField
              label="Video File"
              accept="video/*"
              fileName={videoFileName}
              uploading={videoUploading}
              onUpload={handleVideoUpload}
              icon="🎬"
              hint="Select the source video from your device"
            />
            {videoError && <p style={S.errText}>{videoError}</p>}
            {errorMsg  && <p style={S.errText}>⚠ {errorMsg}</p>}

            <SegmentList
                segments={segments}
                onAdd={() => setSegments(prev => [...prev, { id: crypto.randomUUID(), startTime: "0:00", endTime: "", transitionAfter: "cut" }])}
                onReorder={setSegments}
                onRemove={(i) => setSegments(prev => prev.filter((_, idx) => idx !== i))}
                onUpdate={(i, field, val) => setSegments(prev => {
                  const updated = [...prev];
                  updated[i] = { ...updated[i], [field]: val };
                  return updated;
                })}
                onUpdateTransition={(i, val) => setSegments(prev => {
                  const updated = [...prev];
                  updated[i] = { ...updated[i], transitionAfter: val };
                  return updated;
                })}
              />
            <div style={S.section}>
              <label style={S.label}>Words Per Card <span style={S.val}>{wordsPerCard}</span></label>
              <input type="range" min={1} max={4} step={1}
                value={wordsPerCard} onChange={e => setWordsPerCard(+e.target.value)} style={S.range} />
              <div style={S.ticks}><span>1</span><span>2</span><span>3</span><span>4</span></div>
            </div>

            <div style={S.divider} />
            <StylePanel {...mode1StyleProps} />

            <button style={{ ...S.primaryBtn, marginTop: 24 }} onClick={handleMode1Transcribe}>
              Next — Transcribe Clip →
            </button>
          </div>
        )}

        {/* ══════════════════════════════════════════════════
            MODE 2 — Multiple Clips + Audio Transcription
        ══════════════════════════════════════════════════ */}
        {appMode === "mode2" && !processing && !showReview && (
          <div style={S.card}>
            <button style={S.backChip} onClick={() => setAppMode("landing")}>← Back</button>
            <label style={S.stepTag}>MODE 02 — AUDIO TRANSCRIPTION</label>
            <h2 style={S.cardH}>Clips + Audio Transcription</h2>
            {errorMsg && <p style={S.errText}>⚠ {errorMsg}</p>}

            {/* CLIPS */}
            <div style={S.sectionTitle}>VIDEO CLIPS</div>
            <div style={S.section}>
              <ClipList
                  clips={clips}
                  onAdd={handleClipAdd}
                  onReorder={setClips}
                  onRemove={i => setClips(prev => prev.filter((_, idx) => idx !== i))}
                  onUpdateTransition={(i, val) => setClips(prev => {
                    const updated = [...prev];
                    updated[i] = { ...updated[i], transitionAfter: val };
                    return updated;
                  })}
                  uploading={clipUploading}
                />
            </div>

            <div style={S.divider} />

            <div style={S.sectionTitle}>AUDIO FILE TO TRANSCRIBE</div>
            <div style={S.section}>
              <label style={S.label}>
                Upload Audio <span style={S.optional}>(MP3/WAV — replaces clip audio)</span>
              </label>
              <label style={S.uploadBox}>
                <input type="file" accept="audio/*" style={{ display: "none" }}
                  onChange={handleAudioUpload} />
                {audioUploading
                  ? <span style={{ color: "#f5a623", fontSize: 12 }}>Uploading...</span>
                  : audioFile
                    ? <span style={{ color: "#22c55e", fontSize: 12 }}>✓ {audioFile.filename} ({audioFile.duration?.toFixed(1)}s)</span>
                    : <span style={{ color: "#555", fontSize: 12 }}>Click to upload audio file</span>}
              </label>
              <p style={S.hint}>
                Whisper will transcribe this audio and sync subtitles to it.
                Video plays till clips end regardless.
              </p>
            </div>
            <div style={S.section}>
              <label style={S.label}>Words Per Card <span style={S.val}>{mode2wpc}</span></label>
              <input type="range" min={1} max={4} step={1}
                value={mode2wpc} onChange={e => setMode2wpc(+e.target.value)} style={S.range} />
              <div style={S.ticks}><span>1</span><span>2</span><span>3</span><span>4</span></div>
            </div>
            <div style={S.divider} />

            {/* STYLE PANEL (shared, sizes constrained by TRANSCRIBE_SIZE_MAP) */}
            <StylePanel {...mode2StyleProps} />

            <button style={{ ...S.primaryBtn, marginTop: 24 }} onClick={handleMode2Start}>
              ▶ &nbsp; Generate Reel
            </button>
          </div>
        )}

        {/* ══════════════════════════════════════════════════
            PROCESSING SCREEN (all modes)
        ══════════════════════════════════════════════════ */}
        {processing && (
          <ProcessingScreen
            jobPhase={jobPhase}
            jobStatus={jobStatus}
            progress={progress}
            errorMsg={errorMsg}
            onBack={() => { setProcessing(false); setErrorMsg(""); }}
          />
        )}

        {/* ══════════════════════════════════════════════════
            REVIEW & EDIT SUBTITLES (all modes)
            NEW: each card now has a word-color row underneath it.
        ══════════════════════════════════════════════════ */}
        {showReview && !processing && (
          <div style={S.card}>
            <label style={S.stepTag}>REVIEW SUBTITLES</label>
            <h2 style={S.cardH}>Review & Edit Subtitles</h2>
            <p style={S.cardSub}>
              <strong style={{ color: "#f5a623" }}>{chunks.length} subtitle cards</strong>.
              Edit text, then tap a swatch under any word to make it stand out (e.g. color "starving" red).
            </p>
            {errorMsg && <p style={S.errText}>⚠ {errorMsg}</p>}

            <div style={S.chunksWrap}>
              {chunks.map((chunk, i) => (
                <div key={i} style={S.chunkCard}>
                  <div style={S.chunkRow}>
                    <div style={S.chunkTime}>
                      {Number(chunk.start).toFixed(1)}s – {Number(chunk.end).toFixed(1)}s
                    </div>
                    <input style={S.chunkInput}
                      value={chunk.text}
                      onChange={e => updateChunk(i, e.target.value)}
                    />
                  </div>
                  <WordColorEditor
                    text={chunk.text}
                    wordColors={chunk.wordColors}
                    onSetColor={(wordIdx, color) => setWordColor(i, wordIdx, color)}
                    onClearColor={(wordIdx) => clearWordColor(i, wordIdx)}
                  />
                </div>
              ))}
            </div>

            <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
              <button style={S.backBtn} onClick={reset}>← Start Over</button>
              <button style={{ ...S.primaryBtn, flex: 1 }} onClick={handleRender}>
                ▶ &nbsp; Render Final Video
              </button>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════
            DONE POPUP
        ══════════════════════════════════════════════════ */}
        {showDone && <DonePopup outputPath={outputPath} jobId={jobId} onReset={reset} />}

      </div>
    </div>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const S = {

  root: { minHeight: "100vh", background: "#05070f", color: "#e8e4dc", fontFamily: "'Segoe UI', sans-serif", position: "relative", overflowX: "hidden" },
  noise: { position: "fixed", inset: 0, backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E\")", pointerEvents: "none", zIndex: 0 },
  glow1: { position: "fixed", top: -150, right: -100, width: 500, height: 500, borderRadius: "50%", background: "radial-gradient(circle, #f5a62318 0%, transparent 70%)", pointerEvents: "none", zIndex: 0 },
  glow2: { position: "fixed", bottom: -100, left: -150, width: 400, height: 400, borderRadius: "50%", background: "radial-gradient(circle, #e11d4818 0%, transparent 70%)", pointerEvents: "none", zIndex: 0 },
  page: { position: "relative", zIndex: 1, maxWidth: 860, margin: "0 auto", padding: "40px 20px 100px" },
  header: { marginBottom: 32 },
  headerInner: { display: "flex", alignItems: "center", gap: 16 },
  reel: { fontSize: 40, color: "#f5a623", lineHeight: 1 },
  title: { fontSize: 32, fontWeight: 900, margin: "0 0 4px", letterSpacing: "-0.03em" },
  titleAi: { background: "linear-gradient(135deg,#f5a623,#e11d48)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" },
  subtitle: { fontSize: 11, color: "#555", letterSpacing: "0.08em", margin: 0 },

  // Mode cards (landing)
  modeGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 8 },
  modeCard: { background: "#0b0e1a", border: "1px solid #1a2030", borderRadius: 16, padding: 24, cursor: "pointer", transition: "border-color .2s" },
  modeIcon: { fontSize: 32, marginBottom: 12 },
  modeTitle: { fontSize: 17, fontWeight: 800, margin: "0 0 8px" },
  modeDesc: { fontSize: 12, color: "#666", lineHeight: 1.6, margin: "0 0 12px" },
  modeFeatures: { display: "flex", flexDirection: "column", gap: 4 },
  feat: { fontSize: 11, color: "#f5a623" },

  // Card
  card: { background: "#0b0e1a", border: "1px solid #1a2030", borderRadius: 16, padding: "28px 28px 32px", marginBottom: 20 },
  stepTag: { fontSize: 10, letterSpacing: "0.25em", color: "#f5a623", border: "1px solid #f5a62344", padding: "3px 10px", borderRadius: 3, display: "inline-block", marginBottom: 14 },
  cardH: { fontSize: 20, fontWeight: 800, margin: "0 0 6px" },
  cardSub: { fontSize: 13, color: "#555", margin: "0 0 24px" },
  backChip: { background: "#1a2030", border: "1px solid #2a3040", color: "#888", padding: "5px 14px", borderRadius: 20, fontSize: 12, cursor: "pointer", marginBottom: 16, display: "inline-block" },

  sectionTitle: { fontSize: 10, letterSpacing: "0.2em", color: "#f5a623", marginBottom: 16, fontWeight: 700 },
  divider: { height: 1, background: "#1a2030", margin: "24px 0" },
  section: { marginBottom: 24 },
  label: { fontSize: 11, fontWeight: 700, color: "#888", letterSpacing: "0.15em", textTransform: "uppercase", display: "block", marginBottom: 10 },
  optional: { color: "#444", textTransform: "none", letterSpacing: 0, fontWeight: 400 },
  val: { color: "#f5a623", textTransform: "none", letterSpacing: 0, fontWeight: 700 },
  hint: { fontSize: 11, color: "#444", marginTop: 6 },
  errText: { color: "#f87171", fontSize: 13, margin: "4px 0 12px" },

  pathInput: { width: "100%", background: "#070a12", border: "1px solid #1a2030", borderRadius: 8, color: "#e8e4dc", fontSize: 13, padding: "11px 14px", fontFamily: "monospace", outline: "none", boxSizing: "border-box" },
  timeInput: { width: "100%", background: "#070a12", border: "1px solid #1a2030", borderRadius: 8, color: "#e8e4dc", fontSize: 14, padding: "11px 14px", outline: "none", fontFamily: "monospace", boxSizing: "border-box" },
  textarea: { width: "100%", background: "#070a12", border: "1px solid #1a2030", borderRadius: 8, color: "#e8e4dc", fontSize: 13, padding: "12px 14px", outline: "none", boxSizing: "border-box", resize: "vertical", fontFamily: "'Segoe UI', sans-serif", lineHeight: 1.6 },

  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 32px" },
  select: { width: "100%", background: "#070a12", border: "1px solid #1a2030", color: "#e8e4dc", padding: "10px 14px", borderRadius: 8, fontSize: 14, cursor: "pointer", outline: "none" },
  range: { width: "100%", accentColor: "#f5a623", cursor: "pointer" },
  ticks: { display: "flex", justifyContent: "space-between", fontSize: 10, color: "#444", marginTop: 3 },

  // Fixed-size badge + toggle buttons (replace sliders for font/logo size)
  fixedBadge: { display: "inline-block", background: "#0d1020", border: "1px solid #1a2030", color: "#f5a623", borderRadius: 8, padding: "10px 16px", fontSize: 13, fontWeight: 700 },
  sizeBtn: { flex: 1, background: "#0d1020", border: "1px solid #1a2030", color: "#666", borderRadius: 8, padding: "10px 4px", cursor: "pointer", fontSize: 13, fontWeight: 700, textAlign: "center" },
  sizeBtnOn: { background: "#f5a62318", border: "1px solid #f5a623", color: "#f5a623" },

  // Drop zone / upload box
  dropZone: { display: "block", border: "2px dashed #1a2030", borderRadius: 12, padding: "28px 20px", textAlign: "center", cursor: "pointer", transition: "border-color .2s" },
  uploadBox: { display: "flex", alignItems: "center", justifyContent: "center", border: "1px dashed #2a3040", borderRadius: 8, padding: "14px 20px", cursor: "pointer", gap: 8 },

  // Clip list
  clipRow: { display: "flex", alignItems: "center", gap: 12 },
  clipHandle: { color: "#333", fontSize: 16, flexShrink: 0 },
  clipNum: { fontSize: 11, color: "#f5a623", fontWeight: 700, minWidth: 18, flexShrink: 0 },
  clipName: { fontSize: 12, margin: 0, color: "#ccc", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  clipDur: { fontSize: 11, margin: "2px 0 0", color: "#555" },
  clipRemove: { background: "transparent", border: "none", color: "#555", cursor: "pointer", fontSize: 14, flexShrink: 0 },

  transitionRow:    { display: "flex", alignItems: "center", gap: 8, margin: "4px 0" },
  transitionLine:   { flex: 1, height: 1, background: "#1a2030" },
  transitionSelect: { background: "#0d1020", border: "1px solid #2a3040", color: "#f5a623", fontSize: 11, padding: "4px 8px", borderRadius: 6, cursor: "pointer", outline: "none" },

  // Style cards
  styleCards: { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10 },
  styleCard: { background: "#0d1020", border: "1px solid #1a2030", borderRadius: 10, padding: "14px 12px", cursor: "pointer", textAlign: "center" },
  styleCardActive: { border: "1px solid #f5a623", background: "#f5a62310" },
  stylePreview: { minHeight: 30, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 6 },
  styleName: { fontSize: 12, fontWeight: 700, margin: "0 0 2px" },
  styleDesc: { fontSize: 10, color: "#555", margin: 0 },

  posBtns: { display: "flex", gap: 6 },
  posBtn: { flex: 1, background: "#0d1020", border: "1px solid #1a2030", color: "#666", borderRadius: 8, padding: "8px 4px", cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: 3 },
  posBtnOn: { background: "#f5a62318", border: "1px solid #f5a623", color: "#f5a623" },

  colorRow: { display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" },
  colorPick: { width: 38, height: 32, border: "1px solid #2a3040", borderRadius: 6, cursor: "pointer", padding: 2, background: "none" },
  colorHex: { fontSize: 11, fontFamily: "monospace", color: "#666" },
  presets: { display: "flex", gap: 5 },
  dot: { width: 18, height: 18, borderRadius: "50%", cursor: "pointer" },

  logoGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 },
  logoBtn: { background: "#0d1020", border: "1px solid #1a2030", color: "#666", borderRadius: 6, padding: "8px", cursor: "pointer", fontSize: 11 },
  logoBtnOn: { background: "#f5a62318", border: "1px solid #f5a623", color: "#f5a623" },

  previewScreen: { background: "#000", borderRadius: 10, height: 150, border: "1px solid #1a2030", position: "relative", overflow: "hidden", backgroundImage: "linear-gradient(45deg,#0d0d0d 25%,transparent 25%),linear-gradient(-45deg,#0d0d0d 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#0d0d0d 75%),linear-gradient(-45deg,transparent 75%,#0d0d0d 75%)", backgroundSize: "16px 16px", backgroundPosition: "0 0,0 8px,8px -8px,-8px 0" },
  previewBars: { position: "absolute", inset: 0, display: "flex", flexDirection: "column", justifyContent: "center", gap: 8, padding: 20, opacity: 0.15 },
  previewBar: { height: 5, background: "#fff", borderRadius: 3, width: "80%" },

  // Progress
  progTrack: { height: 8, background: "#141824", borderRadius: 4, overflow: "hidden", marginBottom: 10, position: "relative" },
  progFill: { height: "100%", background: "linear-gradient(90deg,#f5a623,#e11d48)", borderRadius: 4, transition: "width .5s ease", position: "relative", overflow: "hidden" },
  progShine: { position: "absolute", top: 0, left: "-100%", width: "60%", height: "100%", background: "linear-gradient(90deg,transparent,#ffffff44,transparent)", animation: "shine 1.5s infinite" },
  stepRow: { display: "flex", justifyContent: "space-around", marginTop: 20 },
  stepCol: { display: "flex", flexDirection: "column", alignItems: "center", gap: 6 },
  stepBubble: { width: 30, height: 30, borderRadius: "50%", background: "#141824", border: "1px solid #2a3040", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, color: "#555" },
  bubbleDone: { background: "#22c55e22", border: "1px solid #22c55e", color: "#22c55e" },
  bubbleActive: { background: "#f5a62322", border: "1px solid #f5a623", color: "#f5a623" },
  stepLbl: { fontSize: 10, color: "#666", letterSpacing: "0.05em" },

  // Review chunks
  chunksWrap: { maxHeight: 480, overflowY: "auto", display: "flex", flexDirection: "column", gap: 14 },
  chunkCard: { background: "#0d1020", border: "1px solid #1a2030", borderRadius: 10, padding: "10px 12px" },
  chunkRow: { display: "flex", alignItems: "center", gap: 12, marginBottom: 8 },
  chunkTime: { fontSize: 11, fontFamily: "monospace", color: "#f5a623", minWidth: 110, flexShrink: 0 },
  chunkInput: { flex: 1, background: "#070a12", border: "1px solid #1a2030", borderRadius: 6, color: "#e8e4dc", fontSize: 13, padding: "8px 12px", outline: "none", fontWeight: 700 },

  // NEW: per-word color chips (shown under each subtitle card in Review step)
  wordColorRow: { display: "flex", flexWrap: "wrap", gap: 8 },
  wordChip: { display: "flex", flexDirection: "column", alignItems: "center", gap: 4, background: "#070a12", border: "1px solid #1a2030", borderRadius: 8, padding: "6px 8px" },
  wordChipControls: { display: "flex", alignItems: "center", gap: 3 },
  wordDot: { width: 13, height: 13, borderRadius: "50%", cursor: "pointer" },
  wordColorInput: { width: 16, height: 16, border: "none", padding: 0, cursor: "pointer", background: "none", borderRadius: 3 },
  wordClearBtn: { background: "transparent", border: "none", color: "#f87171", cursor: "pointer", fontSize: 12, lineHeight: 1, padding: 0, marginLeft: 2 },

  // Buttons
  primaryBtn: { width: "100%", background: "linear-gradient(135deg,#f5a623,#e11d48)", border: "none", color: "#fff", padding: 15, borderRadius: 10, fontSize: 15, fontWeight: 800, cursor: "pointer", letterSpacing: "0.02em" },
  backBtn: { background: "#1a2030", border: "1px solid #2a3040", color: "#888", padding: "15px 20px", borderRadius: 10, fontSize: 14, cursor: "pointer" },
  modalErr: { marginTop: 20, background: "#f8717122", border: "1px solid #f8717144", color: "#f87171", padding: "12px 16px", borderRadius: 8, fontSize: 13 },
  closeBtn: { background: "transparent", border: "1px solid #f87171", color: "#f87171", padding: "4px 12px", borderRadius: 4, fontSize: 12, cursor: "pointer", marginLeft: 10 },

  // Done modal
  overlay: { position: "fixed", inset: 0, background: "#000000cc", backdropFilter: "blur(10px)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 },
  modal: { background: "#0b0e1a", border: "1px solid #1a2535", borderRadius: 20, padding: 40, maxWidth: 460, width: "100%", textAlign: "center", position: "relative", overflow: "hidden" },
  modalGlow: { position: "absolute", top: -100, left: "50%", transform: "translateX(-50%)", width: 300, height: 200, pointerEvents: "none" },
  modalTitle: { fontSize: 22, fontWeight: 800, margin: "0 0 8px" },
  modalSub: { fontSize: 13, color: "#666", margin: "0 0 24px" },
  checkRing: { width: 64, height: 64, borderRadius: "50%", background: "#22c55e22", border: "2px solid #22c55e", color: "#22c55e", fontSize: 26, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" },
  outBox: { background: "#070a12", border: "1px solid #1a2030", borderRadius: 10, padding: 16, marginBottom: 16, textAlign: "left" },
  outLabel: { fontSize: 10, letterSpacing: "0.2em", color: "#444", display: "block", marginBottom: 6 },
  outPath: { fontSize: 12, fontFamily: "monospace", color: "#22c55e", wordBreak: "break-all", margin: 0 },
};
















