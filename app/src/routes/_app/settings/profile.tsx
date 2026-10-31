import { createFileRoute } from "@tanstack/react-router";
import { ProfilePage } from "@/components/auth/profile-page";

export const Route = createFileRoute("/_app/settings/profile")({
  component: ProfilePage,
});
