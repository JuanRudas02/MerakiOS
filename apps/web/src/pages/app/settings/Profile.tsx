import { ShieldCheck, UserCircle2 } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Section } from "@/components/common/Section";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/features/auth/AuthProvider";
import { ROLE_LABELS } from "@/lib/api";
import { fmtDateTime, initials } from "@/lib/format";

export default function Profile() {
  const { user, workspace } = useAuth();
  if (!user) return null;
  return (
    <div className="space-y-6">
      <PageHeader title="Mi perfil" icon={UserCircle2} />
      <Section>
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
          <Avatar className="h-16 w-16">
            <AvatarFallback className="bg-gradient-heavy text-lg font-semibold text-white">{initials(user.name)}</AvatarFallback>
          </Avatar>
          <div>
            <h2 className="text-xl font-semibold">{user.name}</h2>
            <p className="text-sm text-muted-foreground">{user.email ?? user.username}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge>{ROLE_LABELS[user.role]}</Badge>
              <Badge variant="secondary">{workspace?.name}</Badge>
            </div>
          </div>
        </div>
        <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-muted-foreground">Usuario</dt>
            <dd className="font-medium">{user.username}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Teléfono</dt>
            <dd className="font-medium">{user.phone ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Último acceso</dt>
            <dd className="font-medium">{fmtDateTime(user.last_login_at)}</dd>
          </div>
        </dl>
      </Section>
      <Section title="Permisos de tu rol" description="Definidos por el administrador del workspace.">
        <ul className="flex flex-wrap gap-2">
          {user.permissions.map((p) => (
            <li key={p} className="flex items-center gap-1.5 rounded-md border bg-elevated/50 px-2.5 py-1 font-mono text-xs">
              <ShieldCheck className="h-3.5 w-3.5 text-heavy-mint" aria-hidden /> {p}
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}
