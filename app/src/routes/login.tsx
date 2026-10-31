import { createFileRoute } from "@tanstack/react-router";
import { LoginPage } from "lost-ui/templates/auth/login-page";
import { renderLink } from "@/components/shared/layout/render-link";

const NOT_AVAILABLE = "O login ainda não está disponível nesta versão.";

export const Route = createFileRoute("/login")({
  component: LoginRoute,
});

function LoginRoute() {
  return (
    <LoginPage
      title="Entrar"
      description="Use seu usuário e senha da plataforma Lost Crypto."
      identifier="text"
      identifierLabel="Usuário"
      renderLink={renderLink}
      onSubmit={async () => NOT_AVAILABLE}
    />
  );
}
