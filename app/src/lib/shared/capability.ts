import { Role } from "@/lib/shared/enums";
import type { User } from "@/lib/shared/api/schemas";

export const Capability = {
  BotsControl: "bots.control",
  BotsEdit: "bots.edit",
  BotsPromoteLive: "bots.promote-live",
  BacktestsRun: "backtests.run",
  MarketDataImport: "market-data.import",
  ExchangesManage: "exchanges.manage",
  SystemKillSwitch: "system.kill-switch",
  UsersManage: "users.manage",
} as const;
export type Capability = (typeof Capability)[keyof typeof Capability];

export const can = (user: User | null, capability: Capability): boolean => {
  if (user === null || !user.can_write) return false;
  if (capability === Capability.UsersManage) return user.role === Role.Admin;
  return true;
};

export const WHY_ADMIN_ONLY = "Somente administradores podem fazer isso.";
