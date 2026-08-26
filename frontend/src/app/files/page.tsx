"use client";
import { useEffect, useState } from "react";
import {
  listDocuments,
  uploadDocument,
  updateDocument,
  deleteDocument,
  DocumentItem,
  DocType,
} from "@/api/documents";

type Category = "전체" | DocType;
const TABS: Category[] = ["전체", "규정", "양식", "가이드", "보고서", "기타"];
const DOC_TYPES: DocType[] = ["규정", "양식", "가이드", "보고서", "기타"];

// 파일명을 이름부분/확장자로 분리 (CSS에서 이름부분만 ellipsis 처리, 확장자는 항상 온전히 표시)
function splitFilename(name: string): { base: string; ext: string } {
  const dotIndex = name.lastIndexOf(".");
  if (dotIndex <= 0) return { base: name, ext: "" }; // 확장자 없는 파일명
  return { base: name.slice(0, dotIndex), ext: name.slice(dotIndex) };
}

// 썸네일
function previewKind(fileType: string | null): "doc" | "slide" | "photo" {
  const t = (fileType || "").toLowerCase();
  if (["ppt", "pptx"].includes(t)) return "slide";
  if (["png", "jpg", "jpeg", "gif", "webp"].includes(t)) return "photo";
  return "doc"; // docx / pdf / txt / 기타
}

export default function FilesPage() {
  const [tab, setTab] = useState<Category>("전체");
  const [files, setFiles] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [openMenuId, setOpenMenuId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editDocType, setEditDocType] = useState<DocType>("기타");
  const [showUpload, setShowUpload] = useState(false);

  function refresh() {
    setLoading(true);
    listDocuments()
      .then(setFiles)
      .catch((e) => setError(e.message || "파일 목록을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }

  useEffect(() => { refresh(); }, []);

  const visible = tab === "전체" ? files : files.filter((f) => f.documentType === tab);

  // 수정
  function startEdit(f: DocumentItem) {
    setOpenMenuId(null);
    setEditingId(f.id);
    setEditTitle(f.title);
    setEditDescription(f.description ?? "");
    setEditDocType(f.documentType);
  }

  // 수정 완료
  async function saveEdit(id: number) {
    try {
      const updated = await updateDocument(id, {
        title: editTitle,
        description: editDescription,
        documentType: editDocType,
      });
      setFiles((prev) => prev.map((f) => (f.id === id ? updated : f)));
      setEditingId(null);
    } catch (e: any) {
      alert(e.message || "수정에 실패했습니다.");
    }
  }

  // 삭제
  async function handleDelete(f: DocumentItem) {
    setOpenMenuId(null);
    if (!confirm(`"${f.title}" 파일을 삭제할까요?`)) return;
    try {
      await deleteDocument(f.id);
      setFiles((prev) => prev.filter((x) => x.id !== f.id));
    } catch (e: any) {
      alert(e.message || "삭제에 실패했습니다.");
    }
  }

  return (
    <div>
      {/* files-header */}
      <div className="files-header">
        <h1>파일관리</h1>
        <div className="files-header-bottom">
          <div className="files-tabs">
            {TABS.map((t) => (
              <button
                key={t}
                className={`files-tab ${tab === t ? "active" : ""}`}
                onClick={() => setTab(t)}
              >
                {t}
              </button>
            ))}
          </div>

          <button
            className="files-upload-btn"
            type="button"
            onClick={() => setShowUpload(true)}
          >
            <img src="/icons/plus-white.png" />
            <span>파일 업로드</span>
          </button>
        </div>
      </div>

      {loading && <div style={{ color: "var(--muted)" }}>불러오는 중...</div>}
      {!loading && error && <div style={{ color: "var(--block)" }}>{error}</div>}

      {/* files-grid */}
      {!loading && !error && (
        <div className="files-grid">
          {visible.map((file) => (
            <div className="file-card" key={file.id}>
              <div className="file-thumb">
                {/* TODO: 카테고리별 배지 색상 구분 원하면 documentType 기준으로 클래스 분기 추가 */}
                <span className="file-badge">{file.documentType}</span>
                <button
                  className="file-menu-btn"
                  onClick={() => setOpenMenuId(openMenuId === file.id ? null : file.id)}
                  aria-label="파일 옵션"
                >
                  <img src="/icons/dots.png" />
                </button>

                <FilePreview kind={previewKind(file.fileType)} />

                {openMenuId === file.id && (
                  <div className="file-menu">
                    <button onClick={() => startEdit(file)}>수정</button>
                    <button className="danger" onClick={() => handleDelete(file)}>삭제</button>
                  </div>
                )}
              </div>

              {editingId === file.id ? (
                <div className="file-edit-row">
                  <input
                    className="file-edit-input"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    placeholder="제목"
                    autoFocus
                  />
                  <input
                    className="file-edit-input"
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    placeholder="설명 (선택)"
                  />

                  <select value={editDocType} onChange={(e) => setEditDocType(e.target.value as DocType)}>
                    {DOC_TYPES.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>

                  <button className="file-edit-save" onClick={() => saveEdit(file.id)}>저장</button>
                  <button className="file-edit-cancel" onClick={() => setEditingId(null)}>취소</button>
                </div>
              ) : (
                <div className="file-name" title={file.title}>
                  <span className="file-name-base">{splitFilename(file.title).base}</span>
                  <span className="file-name-ext">{splitFilename(file.title).ext}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 파일이 없을 때 */}
      {!loading && !error && visible.length === 0 && (
        <div style={{ padding: "60px 0", textAlign: "center", color: "var(--muted)" }}>
          해당 분류의 파일이 없어요.
        </div>
      )}

      {showUpload && (
        <UploadModal 
          onClose={() => setShowUpload(false)}
          onUploaded={(doc) => {
            setFiles((prev) => [doc, ...prev]);
            setShowUpload(false);
          }}
        />
      )}
    </div>
  );
}

// 파일 썸네일
function FilePreview({ kind }: { kind: "doc" | "slide" | "photo" }) {
  if (kind === "slide") {
    return (
      <div className="preview-slide">
        <span className="preview-slide-shape" />
      </div>
    );
  }
  if (kind === "photo") {
    return (
      <div className="preview-photo">
        <span className="preview-photo-icon">🖼</span>
      </div>
    );
  }
  // doc / pdf: 텍스트 줄 목업
  return (
    <div className="preview-doc">
      {[90, 70, 80, 60, 75, 50].map((w, i) => (
        <span key={i} className="preview-line" style={{ width: `${w}%` }} />
      ))}
    </div>
  );
}

// 업로드 모달창
function UploadModal({
  onClose,
  onUploaded
}: {
  onClose: () => void,
  onUploaded: (doc: DocumentItem) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [docType, setDocType] = useState<DocType>("기타");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    // 제목을 아직 안 건드렸으면(비어있으면) 파일명으로 자동 채워줌
    if (f && !title.trim()) {
      setTitle(f.name);
    }
  }

  async function submit() {
    if (!file) {
      setErr("파일을 선택해주세요.");
      return;
    }
    if (!title.trim()) {
      setErr("제목을 입력해주세요.");
      return;
    }
    setSubmitting(true);
    setErr("");
    try {
      const doc = await uploadDocument(file, title.trim(), docType, description.trim() || undefined);
      onUploaded(doc);
    } catch (e: any) {
      setErr(e.message || "업로드에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <h2>파일 업로드</h2>

        <label className="modal-label">파일</label>
        <input
          className="modal-input"
          type="file"
          accept=".pdf,.docx,.txt,.md"
          onChange={handleFileChange}
        />

        <label className="modal-label">제목</label>
        <input className="modal-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="예: 이력서 양식.docx" />

        <label className="modal-label">설명 (선택)</label>
        <input
          className="modal-input"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="이 문서가 어떤 내용인지 간단히 적어주세요"
        />

        <label className="modal-label">분류</label>
        <select className="modal-input" value={docType} onChange={(e) => setDocType(e.target.value as DocType)}>
          {DOC_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        {err && <div style={{ color: "var(--block)", fontSize: 12, marginTop: 8 }}>{err}</div>}

        <div className="modal-actions">
          <button className="modal-cancel" onClick={onClose}>취소</button>
          <button className="modal-submit" onClick={submit} disabled={submitting}>
            {submitting ? "업로드 중…" : "업로드"}
          </button>
        </div>
      </div>
    </div>
  );
}
