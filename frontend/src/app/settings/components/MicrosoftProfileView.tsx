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
