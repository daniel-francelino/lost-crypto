import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "lost-ui/app/page-header";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { EmptyState as Empty } from "@/components/shared/feedback/empty-state";
import { Modal } from "lost-ui/elements/modal";
import { Form } from "lost-ui/forms/form";
import { FormInput } from "lost-ui/forms/form-input";
import { FormInputPassword } from "lost-ui/forms/form-input-password";
import { FormSelect } from "lost-ui/forms/form-select";
import { rules } from "lost-ui/forms/rules";
import { Badge } from "lost-ui/ui/badge";
import { Button } from "lost-ui/ui/button";
import { toast } from "lost-ui/ui/sonner";
import { ConfirmDialog } from "@/components/shared/feedback/confirm-dialog";
import { ErrorBlock } from "@/components/shared/feedback/query-boundary";
import { useSessionUser } from "@/hooks/shared/use-session";
import { createUser, listUsers, setUserActive } from "@/lib/auth/auth.api";
import { ApiError } from "@/lib/shared/api/api-error";
import { errorMessage } from "@/lib/shared/api/messages";
import { QueryKey } from "@/lib/shared/api/query-keys";
import type { User } from "@/lib/shared/api/schemas";
import { formatDateTime } from "@/lib/shared/dates";
import { Role } from "@/lib/shared/enums";
import { roleLabel } from "@/lib/shared/labels";

const MIN_PASSWORD = 12;
const ROLE_ITEMS = [
  { label: roleLabel(Role.Admin), value: Role.Admin },
  { label: roleLabel(Role.Viewer), value: Role.Viewer },
];

function NewUserModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const client = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<string>(Role.Viewer);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      createUser(username.trim(), password, role === Role.Admin ? Role.Admin : Role.Viewer),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: QueryKey.Auth.users() });
      toast.success("Usuário criado.");
      setUsername("");
      setPassword("");
      setError(null);
      onOpenChange(false);
    },
    onError: (failure) =>
      setError(
        failure instanceof ApiError && failure.status === 409
          ? "Já existe um usuário com esse nome."
          : errorMessage(failure),
      ),
  });

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Novo usuário">
      <Form onSubmit={() => mutation.mutate()} className="space-y-4">
        <FormInput
          label="Usuário"
          required
          value={username}
          onValueChange={setUsername}
          autoComplete="off"
          rules={[rules.required("Informe o nome de usuário.")]}
        />
        <FormInputPassword
          label="Senha"
          required
          value={password}
          onValueChange={setPassword}
          autoComplete="new-password"
          description={`Pelo menos ${MIN_PASSWORD} caracteres; não pode ser igual ao usuário.`}
          rules={[
            rules.required("Informe a senha."),
            rules.minLength(MIN_PASSWORD, `Use pelo menos ${MIN_PASSWORD} caracteres.`),
          ]}
        />
        <FormSelect label="Papel" items={ROLE_ITEMS} value={role} onValueChange={setRole} />
        {error === null ? null : (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Criando…" : "Criar usuário"}
          </Button>
        </div>
      </Form>
    </Modal>
  );
}

export function UsersPage() {
  const me = useSessionUser();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: QueryKey.Auth.users(),
    queryFn: ({ signal }) => listUsers(signal),
  });
  const [creating, setCreating] = useState(false);
  const [target, setTarget] = useState<User | null>(null);

  const columns: DataTableColumn<User>[] = [
    { id: "username", header: "Usuário", accessor: "username", sortable: true },
    {
      id: "role",
      header: "Papel",
      accessor: "role",
      sortable: true,
      cell: (row) => <Badge variant="secondary">{roleLabel(row.role)}</Badge>,
    },
    {
      id: "status",
      header: "Situação",
      accessor: (row) => (row.is_active ? "ativo" : "desativado"),
      cell: (row) => (
        <Badge variant={row.is_active ? "outline" : "destructive"}>
          {row.is_active ? "Ativo" : "Desativado"}
        </Badge>
      ),
    },
    {
      id: "last_login",
      header: "Último acesso",
      accessor: "last_login_at",
      cell: (row) => formatDateTime(row.last_login_at),
    },
    {
      id: "actions",
      header: "",
      cell: (row) => (
        <Button
          size="sm"
          variant="outline"
          disabled={row.id === me?.id}
          title={row.id === me?.id ? "Você não pode desativar a si mesmo." : undefined}
          onClick={() => setTarget(row)}
        >
          {row.is_active ? "Desativar" : "Reativar"}
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Usuários"
        description="Quem pode entrar na plataforma."
        actions={
          <Button onClick={() => setCreating(true)} className="gap-1.5">
            <UserPlus className="size-4" aria-hidden="true" />
            Novo usuário
          </Button>
        }
      />
      {query.isError && query.data === undefined ? (
        <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <DataTable
          data={query.data ?? []}
          columns={columns}
          getRowId={(row) => row.id}
          rowLabel={(row) => row.username}
          caption="Usuários"
          loading={query.isPending}
          searchable
          searchPlaceholder="Buscar usuário"
          empty={<Empty title="Nenhum usuário" />}
        />
      )}
      <NewUserModal open={creating} onOpenChange={setCreating} />
      <ConfirmDialog
        open={target !== null}
        onOpenChange={(open) => {
          if (!open) setTarget(null);
        }}
        destructive={target?.is_active === true}
        title={
          target?.is_active ? `Desativar ${target.username}?` : `Reativar ${target?.username}?`
        }
        description={
          target?.is_active
            ? "A pessoa perde o acesso: as sessões são encerradas, mas o acesso atual pode durar até 15 minutos."
            : "A pessoa volta a poder entrar."
        }
        confirmLabel={target?.is_active ? "Desativar" : "Reativar"}
        onConfirm={async () => {
          if (target === null) return;
          await setUserActive(target.id, !target.is_active);
          await client.invalidateQueries({ queryKey: QueryKey.Auth.users() });
          toast.success("Usuário atualizado.");
        }}
      />
    </div>
  );
}
