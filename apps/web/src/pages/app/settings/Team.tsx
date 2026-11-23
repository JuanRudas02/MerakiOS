import { useState } from "react";
import { Loader2, Plus, UsersRound } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState } from "@/components/common/States";
import { ListSkeleton } from "@/components/common/Loaders";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/features/auth/AuthProvider";
import { useInviteMember, useMembers } from "@/features/identity/hooks";
import { ROLE_LABELS, type Role } from "@/lib/api";
import { fmtRelative } from "@/lib/format";

export default function Team() {
  const { user } = useAuth();
  const { data, isLoading, error, refetch } = useMembers();
  const invite = useInviteMember();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", role: "staff" as Role, email: "", phone: "", username: "", temporary_password: "" });
  const assignable = (Object.keys(ROLE_LABELS) as Role[]).filter((r) => r !== "owner" && (r !== "admin" || user?.role === "owner"));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Equipo"
        description="Invita personas y asigna roles. Cada rol tiene permisos distintos."
        icon={UsersRound}
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus className="mr-1 h-4 w-4" /> Invitar
          </Button>
        }
      />
      {isLoading ? (
        <ListSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data?.length ? (
        <EmptyState icon={UsersRound} title="Sin miembros" />
      ) : (
        <Card className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nombre</TableHead>
                <TableHead>Rol</TableHead>
                <TableHead className="hidden md:table-cell">Contacto</TableHead>
                <TableHead className="hidden text-right sm:table-cell">Último acceso</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((m) => (
                <TableRow key={m.id}>
                  <TableCell>
                    <p className="font-medium">{m.name}</p>
                    <p className="text-xs text-muted-foreground">{m.username}</p>
                  </TableCell>
                  <TableCell>
                    <StatusBadge tone={m.role === "owner" || m.role === "admin" ? "info" : "neutral"}>{ROLE_LABELS[m.role]}</StatusBadge>
                    {!m.active && (
                      <StatusBadge tone="danger" className="ml-1">
                        Inactivo
                      </StatusBadge>
                    )}
                  </TableCell>
                  <TableCell className="hidden text-sm md:table-cell">{m.email ?? m.phone ?? "—"}</TableCell>
                  <TableCell className="hidden text-right text-sm text-muted-foreground sm:table-cell">{m.last_login_at ? fmtRelative(m.last_login_at) : "Nunca"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invitar miembro</DialogTitle>
            <DialogDescription>Le avisaremos por WhatsApp. La clave temporal NO se envía: compártela por un canal seguro.</DialogDescription>
          </DialogHeader>
          <form
            id="invite-form"
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              invite.mutate(
                {
                  name: form.name,
                  role: form.role,
                  temporary_password: form.temporary_password,
                  email: form.email || undefined,
                  phone: form.phone || undefined,
                  username: form.username || undefined,
                },
                {
                  onSuccess: () => {
                    setOpen(false);
                    setForm({ name: "", role: "staff", email: "", phone: "", username: "", temporary_password: "" });
                  },
                },
              );
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="i-name">Nombre</Label>
              <Input id="i-name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label>Rol</Label>
              <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v as Role })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {assignable.map((r) => (
                    <SelectItem key={r} value={r}>
                      {ROLE_LABELS[r]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="i-email">Email</Label>
              <Input id="i-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="i-phone">WhatsApp</Label>
              <Input id="i-phone" type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="i-user">Usuario (opcional)</Label>
              <Input id="i-user" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="i-pass">Clave temporal</Label>
              <Input id="i-pass" type="text" required minLength={10} autoComplete="off" value={form.temporary_password} onChange={(e) => setForm({ ...form, temporary_password: e.target.value })} />
            </div>
            {!form.email && !form.phone && <p className="text-xs text-muted-foreground sm:col-span-2">Indica email o WhatsApp.</p>}
          </form>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" form="invite-form" disabled={invite.isPending || (!form.email && !form.phone)}>
              {invite.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Invitar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
