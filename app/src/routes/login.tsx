import { createFileRoute, redirect, useRouter } from "@tanstack/react-router";
import { LoginPage } from "lost-ui/templates/auth/login-page";
import { z } from "zod";
import { renderLink } from "@/components/shared/layout/render-link";
import { safeRedirect } from "@/lib/auth/redirect";
import { ApiError, HttpStatus } from "@/lib/shared/api/api-error";
import { NETWORK_ERROR, errorMessage } from "@/lib/shared/api/messages";
import { ensureSession, login } from "@/lib/shared/api/session";

const INVALID_CREDENTIALS = "Usuário ou senha inválidos, ou conta temporariamente bloqueada.";

export const Route = createFileRoute("/login")({
  validateSearch: z.object({ redirect: z.string().optional().catch(undefined) }),
  beforeLoad: async ({ search }) => {
    const user = await ensureSession().catch(() => null);
    if (user !== null) throw redirect({ to: safeRedirect(search.redirect) });
  },
  component: LoginRoute,
});

const loginFailure = (error: unknown): string => {
  if (error instanceof ApiError && error.isNetwork) return NETWORK_ERROR;
  if (error instanceof ApiError && error.hasStatus(HttpStatus.Unauthorized)) {
    return INVALID_CREDENTIALS;
  }
  return errorMessage(error);
};

function LoginRoute() {
  const router = useRouter();
  const search = Route.useSearch();

  return (
    <LoginPage
      title="Entrar"
      description="Use seu usuário e senha da plataforma Lost Crypto."
      identifier="text"
      identifierLabel="Usuário"
      renderLink={renderLink}
      onSubmit={async ({ identifier, password }) => {
        try {
          await login(identifier, password);
        } catch (error) {
          return loginFailure(error);
        }
        router.history.push(safeRedirect(search.redirect));
        return undefined;
      }}
    />
  );
}
