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
