import type { ReceiverProfile } from "@/api/receiverProfiles";

// 직함이 있는 경우(님/씨 생략 가능) + 직함 없이 이름만 있는 경우(님/씨 필수) 둘 다 감지.
// 조사(께/에게/한테)가 실제로 붙어있는 경우만 "받는 사람" 문맥으로 인정한다
export function detectReceiverName(prompt: string): string | null {
  const match = prompt.match(
    /([가-힣]{1,4}\s?(?:사원|대리|과장|차장|팀장|부장|이사|상무|전무))(?:님|씨)?(?=께|에게|한테)|([가-힣]{2,4})(?:님|씨)(?=께|에게|한테)/
  );
  return match ? (match[1] ?? match[2]) : null;
}

const RECEIVER_TITLES = ["사원", "대리", "과장", "차장", "팀장", "부장", "이사", "상무", "전무"];

// 동명이인 후보 비교용으로만 쓰는 분해값. 실제 저장(receiverName)은 항상 detectReceiverName이
// 반환한 원본 문자열 그대로 쓰고, 이건 "같은 사람일 가능성"을 판단하는 용도로만 쓴다.
// 성/이름/직함 중 실제로 못 뽑아낸 조각은 빈 문자열로 비워두고, 나중에 필요하면
// 히스토리 > 수신자별 스타일 관리에서 사용자가 직접 보완하는 걸 전제로 한다
// (단, receiverName 자체를 고치는 PATCH는 지금 백엔드에 아직 없어서 그 UI는 별도 작업 필요).
export type ReceiverNameParts = {
  surname: string;    // 성 - 1글자로 가정 (남궁/독고 같은 2글자 복성은 고려 안 함)
  givenName: string;  // 이름
  title: string;      // 직함
};

export function parseReceiverName(raw: string): ReceiverNameParts {
  for (const title of RECEIVER_TITLES) {
    const idx = raw.indexOf(title);
    if (idx >= 0) {
      // 직함을 빼고 남은 부분이 이름(성+이름). "김민준 대리"면 "김민준 ", "김대리"면 "김".
      const namePart = (raw.slice(0, idx) + raw.slice(idx + title.length)).trim();
      return {
        surname: namePart.slice(0, 1),
        givenName: namePart.slice(1),
        title,
      };
    }
  }
  // 직함이 아예 안 잡히면 raw 전체가 이름 (예: "예진")
  return { surname: raw.slice(0, 1), givenName: raw.slice(1), title: "" };
}

// 성+이름+직함 셋 다 같아야 "확실히 같은 사람"이지만, 그건 exact match(문자열 완전일치)로
// 이미 커버됨. 여기서는 그보다 느슨하게 - 아래 세 쌍 중 하나라도 "둘 다 비어있지 않고 값이
// 같으면" 동명이인 후보로 본다: (성+직함) / (성+이름) / (이름+직함).
// 한쪽에만 있고 다른 쪽엔 없는 조각(예: 직함)은 그냥 빈 문자열로 취급되어 비교에서 빠진다.
//
// + 보강 규칙(2026-09-03): "형돈 대리"처럼 성을 빼고 이름만으로 부르는 경우, parseReceiverName은
// 첫 글자를 성으로 잘못 쪼갠다("형"을 성으로, "돈"을 이름으로). 이러면 위 세 쌍 중 어느 것도
// 안 맞아서 "정형돈 대리"/"정형돈"과 전혀 매칭이 안 되는 문제가 있었다. 이를 보완하기 위해,
// 직함이 같고 한쪽의 "성+이름 전체"가 다른 쪽 "성+이름 전체" 안에 부분 문자열로 포함되면
// (예: "형돈"이 "정형돈"에 포함) 그것도 후보로 인정한다. 1글자짜리 우연한 일치로 오탐하는 걸
// 막기 위해 두 글자 이상일 때만 비교한다.
function fullNamePart(parts: ReceiverNameParts): string {
  return parts.surname + parts.givenName;
}

function partsLikelyMatch(a: ReceiverNameParts, b: ReceiverNameParts): boolean {
  const sameSurname = a.surname !== "" && a.surname === b.surname;
  const sameGivenName = a.givenName !== "" && a.givenName === b.givenName;
  const sameTitle = a.title !== "" && a.title === b.title;

  if ((sameSurname && sameTitle) || (sameSurname && sameGivenName) || (sameGivenName && sameTitle)) {
    return true;
  }

  const aFull = fullNamePart(a);
  const bFull = fullNamePart(b);
  const containsMatch =
    aFull.length >= 2 && bFull.length >= 2 && (aFull.includes(bFull) || bFull.includes(aFull));

  return containsMatch && sameTitle;
}

export type ReceiverMatchResult = {
  // 저장된 이름과 완전히 똑같은 프로필. 있으면 확실한 매칭이라 더 물어볼 필요 없음.
  exact: ReceiverProfile | null;
  // 하위 호환용 - candidates[0]과 동일. exact가 없을 때, 성/이름/직함 중 두 조각이
  // 겹치는 "동명이인일 수 있는" 후보 중 첫 번째.
  candidate: ReceiverProfile | null;
  // 2026-09-03 추가: 겹치는 후보가 여러 명일 수 있다("정대리"가 "정형돈 대리"와
  // "정준하 대리" 둘 다와 매칭되는 경우). 예전엔 find()로 첫 번째만 잡고 나머지는
  // 존재 자체를 감췄는데, 이제 전부 반환해서 UI에서 사용자가 직접 고를 수 있게 한다.
  candidates: ReceiverProfile[];
};

export function matchReceiverProfile(
  name: string,
  profiles: ReceiverProfile[]
): ReceiverMatchResult {
  const exact = profiles.find((p) => p.receiverName === name) ?? null;
  if (exact) return { exact, candidate: null, candidates: [] };

  const parts = parseReceiverName(name);
  const candidates = profiles.filter((p) => partsLikelyMatch(parts, parseReceiverName(p.receiverName)));
  return { exact: null, candidate: candidates[0] ?? null, candidates };
}

// 동명이인 확인 다이얼로그에서 "네, 같은 사람이에요"를 눌렀을 때 쓰는 이름 합성기.
// 두 표기(기존 저장명 vs 새로 감지된 이름) 중 성+이름이 더 완전한(긴) 쪽을 채택하고,
// 직함은 둘 중 있는 쪽을 채운다.
//
// 2026-09-03 수정: 예전엔 무조건 nameA(기존 저장명)의 성/이름을 우선했는데, nameA가
// "형돈 대리"처럼 성 없이 이름만 있는 표기로 먼저 저장돼 있으면 그 잘못 쪼개진 조각이
// 그대로 채택되어("형돈 대리"+"정형돈" → "형돈 대리") 오히려 정보가 사라지는 문제가
// 있었다. "더 긴(완전한) 쪽이 이긴다"로 바꾸면 어느 쪽이 먼저 저장돼 있었는지와 무관하게
// 항상 가장 완전한 형태로 수렴한다.
export function buildCanonicalReceiverName(nameA: string, nameB: string): string {
  const a = parseReceiverName(nameA);
  const b = parseReceiverName(nameB);

  const aFull = a.surname + a.givenName;
  const bFull = b.surname + b.givenName;
  const fullName = aFull.length >= bFull.length ? aFull : bFull;
  const title = a.title || b.title;

  return title ? `${fullName} ${title}` : fullName;
}
