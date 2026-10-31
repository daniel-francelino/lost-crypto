import { redirect } from "@tanstack/react-router";
import { getSessionUser } from "@/lib/shared/api/session";
import { type Capability, can } from "@/lib/shared/capability";
import { AppRoute } from "@/lib/shared/routes";

export const requireCapability = (capability: Capability): void => {
  if (!can(getSessionUser(), capability)) throw redirect({ to: AppRoute.Forbidden });
};
