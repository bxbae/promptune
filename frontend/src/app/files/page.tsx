"use client";
import { useState } from "react";

type Category = "전체" | "일반" | "업무";
type FileType = "doc" | "pdf" | "slide" | "photo";

interface FileItem {
  id: string;
  name: string;
  category: "일반" | "업무";
  type: FileType;
}

// TODO : mock 데이터 - 실제로는 백엔드 /api/files 목록 조회로 교체
const FILES: FileItem[] = [
  { id: "1", name: "이력서 양식3.docx", category: "일반", type: "doc" },
  { id: "2", name: "제안서 양식.pptx", category: "업무", type: "slide" },
  { id: "3", name: "브로슈어.pdf", category: "업무", type: "photo" },
  { id: "4", name: "이력서 양식2.docx", category: "일반", type: "doc" },
  { id: "5", name: "프로젝트 보고서.docx", category: "업무", type: "photo" },
  { id: "6", name: "이력서 양식.docx", category: "일반", type: "doc" },
  { id: "7", name: "온보딩 노트.docx", category: "일반", type: "doc" },
];

const TABS: Category[] = ["전체", "일반", "업무"];

// 파일명이 길 때 확장자는 남기고 앞부분만 ...으로 줄이는 로직
function truncateFilename(name: string, maxChars = 16): string {
  const dotIndex = name.lastIndexOf(".");
  if (dotIndex <= 0) return name; // 확장자 없는 파일명

  const base = name.slice(0, dotIndex);
  const ext = name.slice(dotIndex);   // .확장자
  const maxBase = maxChars - ext.length;

  if (base.length <= maxBase) return name; // 짧으면 그대로
  
  return base.slice(0, Math.max(maxBase - 1, 1)) + "..." + ext;
}

export default function FilesPage() {
  const [tab, setTab] = useState<Category>("전체");
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  const visible = tab === "전체" ? FILES : FILES.filter((f) => f.category === tab);

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
          
          <button className="files-upload-btn" type="button">
            <img src="/icons/plus-white.png" />
            <span>파일 업로드</span>
          </button>
        </div>

      </div>

      {/* files-grid */}
      <div className="files-grid">
        {visible.map((file) => (
          <div className="file-card" key={file.id}>
            <div className="file-thumb">
              <span className={`file-badge ${file.category === "업무" ? "work" : ""}`}>{file.category}</span>
              <button
                className="file-menu-btn"
                onClick={() => setOpenMenuId(openMenuId === file.id ? null : file.id)}
                aria-label="파일 옵션"
              >
                <img src="/icons/dots.png" />
              </button>

              <FilePreview type={file.type} />

              {openMenuId === file.id && (
                <div className="file-menu">
                  <button onClick={() => setOpenMenuId(null)}>수정</button>
                  <button className="danger" onClick={() => setOpenMenuId(null)}>삭제</button>
                </div>
              )}

            </div>

            <div className="file-name" title={file.name}>{truncateFilename(file.name)}</div>
          </div>
        ))}
      </div>

      {/* 파일이 없을 때 */}
      {visible.length === 0 && (
        <div style={{ padding: "60px 0", textAlign: "center", color: "var(--muted)" }}>
          해당 분류의 파일이 없어요.
        </div>
      )}
    </div>
  );
}

// 파일 썸네일
function FilePreview({ type }: { type: FileType }) {
  if (type === "slide") {
    return (
      <div className="preview-slide">
        <span className="preview-slide-shape" />
      </div>
    );
  }
  if (type === "photo") {
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