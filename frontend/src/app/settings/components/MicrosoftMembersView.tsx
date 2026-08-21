import { MicrosoftMember } from "@/lib/microsoft";

type Props = {
  members: MicrosoftMember[];
};

export default function MicrosoftMembersView({ members }: Props) {
  if (members.length === 0) {
    return <div className="ms-members-empty">불러온 구성원이 없어요.</div>;
  }

  return (
    <div className="ms-members-view">
      {members.map((m) => (
        <div className="ms-member-row" key={m.id}>
          <div className="ms-member-avatar">{m.displayName.slice(0, 1)}</div>
          <div className="ms-member-info">
            <div className="ms-member-name">{m.displayName}</div>
            <div className="ms-member-meta">{m.department} · {m.jobTitle}</div>
          </div>
          <div className="ms-member-mail">{m.mail}</div>
        </div>
      ))}
    </div>
  );
}
