type Props = {
  data: any;
};

// userPrincipalName은 Microsoft Entra ID(Azure AD) 게스트 사용자 UPN 형식
// 원래 이메일의 @가 _로 바뀌고, 뒤에 #EXT#@테넌트도메인이 붙는 방식
function formatTenantEmail(upn: string): string {
  if (!upn) return "연결된 회사 계정 없음";
  const parts = upn.split("#EXT#@");
  return parts[1] ?? upn; // 테넌트 도메인이 있으면 그 부분만, 없으면 원래 UPN 그대로;
}

export default function MicrosoftProfileView({ data }: Props) {
  const rows = [
    ["사용자 이름", data.displayName],
    ["회사 이메일/계정", formatTenantEmail(data.userPrincipalName || data.mail)],
    ["회사명", data.companyName],
    ["부서", data.department],
    ["직함/직급", data.jobTitle],
    ["Microsoft 사용자 ID", data.id],
  ];

  return (
    <div className="ms-profile-view">
      {rows.map(([label, value]) => (
        <div className="ms-profile-row" key={label}>
          <span className="ms-profile-label">{label}</span>
          <span className="ms-profile-value">{value || "-"}</span>
        </div>
      ))}
    </div>
  );
}
