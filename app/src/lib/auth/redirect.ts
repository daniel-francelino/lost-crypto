import { AppRoute } from "@/lib/shared/routes";

export const safeRedirect = (target: string | undefined): string => {
  if (target === undefined || !target.startsWith("/") || target.startsWith("//")) {
    return AppRoute.Home;
  }
  if (target.includes("\\") || target.startsWith(AppRoute.Login)) return AppRoute.Home;
  return target;
};
