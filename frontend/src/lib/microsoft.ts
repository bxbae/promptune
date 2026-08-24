import { getToken } from "./auth";

const API =
  process.env.NEXT_PUBLIC_API_URL ||
  ["http", "://", "localhost:8080"].join("");

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function microsoftStatus() {
  const res = await fetch(
    `${API}/api/integrations/microsoft/status`,
    { headers: authHeaders() }
  );

  if (!res.ok) throw new Error("Microsoft 연결 상태 조회 실패");
  return res.json();
}

export async function microsoftConnect() {
  const res = await fetch(
    `${API}/api/integrations/microsoft/connect`,
    { headers: authHeaders() }
  );

  if (!res.ok) throw new Error("Microsoft 연결 시작 실패");
  return res.json();
}

export async function microsoftDisconnect() {
  const res = await fetch(
    `${API}/api/integrations/microsoft`,
    {
      method: "DELETE",
      headers: authHeaders(),
    }
  );

  if (!res.ok) throw new Error("Microsoft 연결 해제 실패");
  return res.json();
}

export async function microsoftEvents() {
  const res = await fetch(
    `${API}/api/integrations/microsoft/events`,
    { headers: authHeaders() }
  );

  if (!res.ok) throw new Error("캘린더 조회 실패");
  return res.json();
}

export async function microsoftFiles() {
  const res = await fetch(
    `${API}/api/integrations/microsoft/files`,
    { headers: authHeaders() }
  );

  if (!res.ok) throw new Error("OneDrive 조회 실패");
  return res.json();
}

export async function microsoftMessages() {
  const res = await fetch(
    `${API}/api/integrations/microsoft/messages`,
    { headers: authHeaders() }
  );

  if (!res.ok) throw new Error("메일 조회 실패");
  return res.json();
}

export async function microsoftProfile() {
  const res = await fetch(
    `${API}/api/integrations/microsoft/profile`,
    { headers: authHeaders() }
  );

  if (!res.ok) throw new Error("Microsoft 프로필 조회 실패");
  return res.json();
}

// 조직 구성원 프로필 목록. 백엔드가 MS Graph의 /v1.0/users를 그대로 감싸서 내려주기 때문에
// 응답이 { value: [...] } 형태(Graph API 원본 포맷)로 옴 - value만 꺼내서 매핑.
export interface MicrosoftMember {
  id: string;
  displayName: string;
  mail: string;
  jobTitle: string;
  department: string;
}

interface GraphUsersResponse {
  value: Array<{
    id: string;
    displayName: string | null;
    mail: string | null;
    jobTitle: string | null;
    department: string | null;
  }>;
}

export async function microsoftMembers(): Promise<MicrosoftMember[]> {
  const res = await fetch(
    `${API}/api/integrations/microsoft/users`,
    { headers: authHeaders() }
  );

  if (!res.ok) throw new Error("구성원 프로필 조회 실패");
  const data: GraphUsersResponse = await res.json();
  return data.value.map((u) => ({
    id: u.id,
    displayName: u.displayName || "(이름 없음)",
    mail: u.mail || "-",
    jobTitle: u.jobTitle || "-",
    department: u.department || "-",
  }));
}
