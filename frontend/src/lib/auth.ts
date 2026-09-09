// 인증 API 호출 + 토큰 관리
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface AuthResponse { token: string; email: string; name: string; }

export async function signup(email: string, password: string, name: string): Promise<AuthResponse> {
  const res = await fetch(`${API}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) throw new Error((await res.json()).error || "회원가입 실패");
  return res.json();
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error((await res.json()).error || "로그인 실패");
  return res.json();
}

// 토큰은 메모리+localStorage (목업). 실서비스는 httpOnly 쿠키 권장.
export function saveToken(token: string) {
  if (typeof window !== "undefined") localStorage.setItem("pt_token", token);
}
export function getToken(): string | null {
  if (typeof window !== "undefined") return localStorage.getItem("pt_token");
  return null;
}
export function logout() {
  if (typeof window !== "undefined") localStorage.removeItem("pt_token");
}
export interface CurrentUser {
  email: string;
  name: string;
  provider?: string;
}
export function getCurrentUser(): CurrentUser | null {
  const token = getToken();
  if (!token) return null;
  try {
    const payload = JSON.parse(
      atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))
    );
    const email = payload.sub || payload.email;
    if (!email) return null;
    return { email, name: payload.name || email.split("@")[0] };
  } catch {
    return null;
  }
}
function authHeaders(): HeadersInit {
  const token = getToken();
  if (!token) throw new Error("로그인이 필요합니다.");
  return { Authorization: `Bearer ${token}` };
}

// JWT보다 DB의 최신 users.name을 우선 사용하기 위한 현재 사용자 조회.
export async function fetchCurrentUser(): Promise<CurrentUser> {
  const res = await fetch(`${API}/api/users/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`계정 정보 조회 실패: ${res.status}`);
  const data = await res.json();
  return {
    email: data.email,
    name: data.name || data.email?.split("@")[0] || "",
    provider: data.provider,
  };
}

export async function updateCurrentUserName(name: string): Promise<CurrentUser> {
  const trimmed = name.trim();
  if (!trimmed) throw new Error("이름을 입력해주세요.");

  const res = await fetch(`${API}/api/users/me/name`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ name: trimmed }),
  });

  if (!res.ok) {
    let message = `이름 수정 실패: ${res.status}`;
    try {
      const data = await res.json();
      message = data.message || data.error || message;
    } catch {}
    throw new Error(message);
  }

  const data = await res.json();
  const updated: CurrentUser = {
    email: data.email,
    name: data.name || trimmed,
    provider: data.provider,
  };

  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent<CurrentUser>("user-profile-updated", { detail: updated }));
  }
  return updated;
}
