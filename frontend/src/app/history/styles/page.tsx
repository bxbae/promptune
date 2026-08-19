"use client";
import { useEffect, useState } from "react";
import {
  listReceiverProfiles,
  updateReceiverProfile,
  deleteReceiverProfile,
  ReceiverProfile,
} from "@/api/receiverProfiles";

export default function StylesPage() {
  const [profiles, setProfiles] = useState<ReceiverProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editRelationship, setEditRelationship] = useState("");
  const [editTone, setEditTone] = useState("");

  function refresh() {
    setLoading(true);
    listReceiverProfiles()
      .then(setProfiles)
      .catch((e) => setError(e.message || "수신자 목록을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }

  useEffect(() => { refresh(); }, []);

  function startEdit(p: ReceiverProfile) {
    setEditingId(p.id);
    setEditRelationship(p.relationship ?? "");
    setEditTone(p.preferredTone ?? "");
  }

  async function saveEdit(id: number) {
    try {
      const updated = await updateReceiverProfile(id, {
        relationship: editRelationship || null,
        preferredTone: editTone || null,
      });
      setProfiles((prev) => prev.map((p) => (p.id === id ? updated : p)));
      setEditingId(null);
    } catch (e: any) {
      alert(e.message || "수정에 실패했습니다.");
    }
  }

  // TODO: 실제 구현 시 확인 모달 필요 (스토리보드 17p 안내 문구) - 우선 confirm()으로 대체
  async function handleDelete(p: ReceiverProfile) {
    if (!confirm(`"${p.receiverName}" 수신자의 학습된 스타일을 초기화할까요?`)) return;
    try {
      await deleteReceiverProfile(p.id);
      setProfiles((prev) => prev.filter((x) => x.id !== p.id));
    } catch (e: any) {
      alert(e.message || "삭제에 실패했습니다.");
    }
  }

  if (loading) {
    return <div style={{ padding: "20px 0", color: "var(--muted)" }}>불러오는 중...</div>;
  }

  if (error) {
    return <div style={{ padding: "20px 0", color: "var(--block)" }}>{error}</div>;
  }

  if (profiles.length === 0) {
    return (
      <div style={{ padding: "40px 0", textAlign: "center", color: "var(--muted)" }}>
        아직 학습된 수신자 스타일이 없어요.<br />
        채팅에서 "OO님께 ~"처럼 수신자를 지정해 대화하면 여기 쌓이기 시작해요.
      </div>
    );
  }

  return (
    <div>
      <p style={{ color: "var(--muted)", marginTop: 0, marginBottom: 20 }}>
        수신자별로 학습된 톤·길이예요. 여기서 직접 수정하거나 초기화할 수 있어요.
      </p>

      <div className="receiver-table">
        <div className="receiver-row receiver-row-head">
          <div>수신자</div>
          <div>관계</div>
          <div>선호 톤</div>
          <div>평균 길이</div>
          <div>적용률</div>
          <div></div>
        </div>

        {profiles.map((p) => (
          <div className="receiver-row" key={p.id}>
            {editingId === p.id ? (
              <>
                <div className="receiver-name">{p.receiverName}</div>
                <div>
                  <input
                    className="receiver-edit-input"
                    value={editRelationship}
                    onChange={(e) => setEditRelationship(e.target.value)}
                    placeholder="예: 같은 팀 동료"
                  />
                </div>
                <div>
                  <input
                    className="receiver-edit-input"
                    value={editTone}
                    onChange={(e) => setEditTone(e.target.value)}
                    placeholder="예: 정중하게"
                  />
                </div>
                <div>{p.avgLength}자</div>
                <div>{p.applyRate != null ? `${Math.round(p.applyRate * 100)}%` : "-"}</div>
                <div className="receiver-actions">
                  <button className="receiver-save" onClick={() => saveEdit(p.id)}>저장</button>
                  <button className="receiver-cancel" onClick={() => setEditingId(null)}>취소</button>
                </div>
              </>
            ) : (
              <>
                <div className="receiver-name">{p.receiverName}</div>
                <div>{p.relationship || "-"}</div>
                <div>{p.preferredTone || "-"}</div>
                <div>{p.avgLength}자</div>
                <div>{p.applyRate != null ? `${Math.round(p.applyRate * 100)}%` : "-"}</div>
                <div className="receiver-actions">
                  <button className="receiver-edit-btn" onClick={() => startEdit(p)}>수정</button>
                  <button className="receiver-delete-btn" onClick={() => handleDelete(p)}>삭제</button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
