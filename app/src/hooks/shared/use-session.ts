import { useSyncExternalStore } from "react";
import { getSessionUser, subscribeSession } from "@/lib/shared/api/session";
import type { User } from "@/lib/shared/api/schemas";

export const useSessionUser = (): User | null =>
  useSyncExternalStore(subscribeSession, getSessionUser, () => null);
