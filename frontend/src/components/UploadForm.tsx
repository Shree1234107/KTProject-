import { FormEvent, useRef, useState } from "react";
import type { MatchResult } from "../types";
import "./UploadForm.css";

interface Props {
  onResult: (result: MatchResult) => void;
  onError: (message: string) => void;
  onLoading: (loading: boolean) => void;
  isLoading: boolean;
}

export default function UploadForm({ onResult, onError, onLoading, isLoading }: Props) {
  const [fileName, setFileName] = useState<string>("");
  const [jd, setJd] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File | null) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      onError("Only PDF files are accepted.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      onError("File exceeds the 5 MB size limit.");
      return;
    }
    setFileName(file.name);
    if (fileRef.current) {
      const dt = new DataTransfer();
      dt.items.add(file);
      fileRef.current.files = dt.files;
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) { onError("Please select a resume PDF."); return; }
    if (!jd.trim() || jd.trim().length < 50) {
      onError("Please paste a job description (at least 50 characters).");
      return;
    }

    onLoading(true);
    const form = new FormData();
    form.append("resume", file);
    form.append("job_description", jd.trim());

    try {
      const res = await fetch("/api/analyze", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Analysis failed.");
      onResult(data as MatchResult);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unexpected error.");
    } finally {
      onLoading(false);
    }
  };

  return (
    <form className="upload-form" onSubmit={handleSubmit}>
      <div className="form-section">
        <label className="form-label">Resume PDF</label>
        <div
          className={`drop-zone${dragOver ? " drop-zone--active" : ""}${fileName ? " drop-zone--filled" : ""}`}
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            handleFile(e.dataTransfer.files[0]);
          }}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,application/pdf"
            style={{ display: "none" }}
            onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          />
          <div className="drop-zone__icon">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <path d="M6 26h20M16 6v14M10 12l6-6 6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          {fileName ? (
            <p className="drop-zone__name">{fileName}</p>
          ) : (
            <p className="drop-zone__hint">
              <strong>Click to upload</strong> or drag and drop<br />
              <span>PDF only · max 5 MB</span>
            </p>
          )}
        </div>
      </div>

      <div className="form-section">
        <label className="form-label" htmlFor="jd">Job Description</label>
        <textarea
          id="jd"
          className="jd-textarea"
          placeholder="Paste the full job description here…"
          value={jd}
          onChange={(e) => setJd(e.target.value)}
          rows={10}
          minLength={50}
        />
        <p className="char-hint">{jd.length} chars (min 50)</p>
      </div>

      <button className="submit-btn" type="submit" disabled={isLoading}>
        {isLoading ? (
          <span className="btn-loading">
            <span className="spinner" />
            Analyzing…
          </span>
        ) : (
          "Analyze Resume"
        )}
      </button>
    </form>
  );
}
