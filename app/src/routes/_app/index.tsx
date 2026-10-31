import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "lost-ui/app/page-header";
import { Empty } from "lost-ui/data/empty";

export const Route = createFileRoute("/_app/")({
  component: DashboardPage,
});

function DashboardPage() {
  return (
    <>
      <PageHeader title="Painel" description="Visão geral dos bots e do sistema." />
      <Empty title="Em construção" description="O painel chega junto com a leitura dos bots." />
    </>
  );
}
