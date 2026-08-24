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

// TODO: (목업) 조직 구성원 프로필 목록 - 백엔드에 아직 이 엔드포인트가 없음.
// MS Graph의 /users(조직 디렉터리 조회)를 백엔드가 감싸서 GET /api/integrations/microsoft/members
// 같은 엔드포인트를 추가해주면, 이 함수 내용만 실제 fetch로 교체하면 됨.
export interface MicrosoftMember {
  id: string;
  displayName: string;
  mail: string;
  jobTitle: string;
  department: string;
}

const MOCK_MEMBERS: MicrosoftMember[] = [
  { id: "1", displayName: "김대리", mail: "kim.d@company.com", jobTitle: "대리", department: "마케팅팀" },
  { id: "2", displayName: "박팀장", mail: "park.t@company.com", jobTitle: "팀장", department: "개발팀" },
  { id: "3", displayName: "이사원", mail: "lee.s@company.com", jobTitle: "사원", department: "영업팀" },
];

export async function microsoftMembers(): Promise<MicrosoftMember[]> {
  // 실제 API 붙기 전까지 약간의 지연으로 로딩 상태를 확인할 수 있게 함
  await new Promise((resolve) => setTimeout(resolve, 300));
  return MOCK_MEMBERS;
}
