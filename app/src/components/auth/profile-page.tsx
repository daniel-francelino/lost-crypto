import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { PageHeader } from "lost-ui/app/page-header";
import { Form } from "lost-ui/forms/form";
import { FormInputPassword } from "lost-ui/forms/form-input-password";
import { rules } from "lost-ui/forms/rules";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import { toast } from "lost-ui/ui/sonner";
import { useSessionUser } from "@/hooks/shared/use-session";
import { changePassword } from "@/lib/auth/auth.api";
import { ApiError, HttpStatus } from "@/lib/shared/api/api-error";
import { errorMessage } from "@/lib/shared/api/messages";
import { clearSession } from "@/lib/shared/api/session";
import { formatDateTime } from "@/lib/shared/dates";
import { roleLabel } from "@/lib/shared/labels";
import { AppRoute } from "@/lib/shared/routes";

const MIN_PASSWORD = 12;

const failureText = (error: unknown): string =>
  error instanceof ApiError && error.hasStatus(HttpStatus.Unauthorized)
    ? "A senha atual está incorreta."
    : errorMessage(error);

export function ProfilePage() {
  const user = useSessionUser();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setPending(true);
    setError(null);
    try {
      await changePassword(current, next);
    } catch (failure) {
      setError(failureText(failure));
      setPending(false);
      return;
    }
    clearSession();
    toast.success("Senha alterada. Entre de novo.");
    await navigate({ to: AppRoute.Login });
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Meu perfil" description="Seus dados e a troca de senha." />
      <Card>
        <CardHeader>
          <CardTitle>{user?.username}</CardTitle>
          <CardDescription>
            {user === null ? "" : roleLabel(user.role)} · último acesso{" "}
            {formatDateTime(user?.last_login_at ?? null)}
          </CardDescription>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Trocar senha</CardTitle>
          <CardDescription>
            Ao trocar a senha você sai de todos os dispositivos, inclusive deste.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form onSubmit={() => void submit()} className="max-w-md space-y-4">
            <FormInputPassword
              label="Senha atual"
              required
              value={current}
              onValueChange={setCurrent}
              autoComplete="current-password"
              rules={[rules.required("Informe a senha atual.")]}
            />
            <FormInputPassword
              label="Nova senha"
              required
              value={next}
              onValueChange={setNext}
              autoComplete="new-password"
              description={`Pelo menos ${MIN_PASSWORD} caracteres.`}
              rules={[
                rules.required("Informe a nova senha."),
                rules.minLength(MIN_PASSWORD, `Use pelo menos ${MIN_PASSWORD} caracteres.`),
              ]}
            />
            <FormInputPassword
              label="Confirmar nova senha"
              required
              value={confirm}
              onValueChange={setConfirm}
              autoComplete="new-password"
              rules={[rules.matches(() => next, "As senhas não conferem.")]}
            />
            {error === null ? null : (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            <Button type="submit" disabled={pending}>
              {pending ? "Salvando…" : "Trocar senha"}
            </Button>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
