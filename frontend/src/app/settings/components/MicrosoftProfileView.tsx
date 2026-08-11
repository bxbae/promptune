type Props = {
  data: any;
};

export default function MicrosoftProfileView({ data }: Props) {
  const rows = [
    ["사용자 이름", data.displayName],
    ["회사 이메일/계정", data.userPrincipalName || data.mail],
    ["회사명", data.companyName],
    ["부서", data.department],
    ["직함/직급", data.jobTitle],
    ["Microsoft 사용자 ID", data.id],
  ];

  return (
    <div style={{ marginTop: 24 }}>
      <h3>Microsoft 프로필</h3>

      {rows.map(([label, value]) => (
        <div
          key={label}
          style={{
            display: "grid",
            gridTemplateColumns: "180px 1fr",
            padding: "10px 0",
            borderBottom: "1px solid #eee",
          }}
        >
          <strong>{label}</strong>
          <span>{value || "-"}</span>
        </div>
      ))}
    </div>
  );
}
