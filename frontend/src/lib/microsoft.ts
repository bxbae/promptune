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
