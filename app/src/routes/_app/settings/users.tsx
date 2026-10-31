import { createFileRoute } from "@tanstack/react-router";
import { UsersPage } from "@/components/auth/users-page";
import { requireCapability } from "@/lib/shared/route-guards";
import { Capability } from "@/lib/shared/capability";

export const Route = createFileRoute("/_app/settings/users")({
  beforeLoad: () => requireCapability(Capability.UsersManage),
  component: UsersPage,
});
