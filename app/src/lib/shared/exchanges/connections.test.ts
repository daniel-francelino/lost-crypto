import { describe, expect, it } from "vitest";
import { permissionItems } from "@/lib/shared/exchanges/connections.api";

describe("key permissions", () => {
  it("marks a trade-only, IP-restricted key as all good", () => {
    const items = permissionItems({
      can_read: true,
      can_trade: true,
      can_withdraw: false,
      can_transfer: false,
      ip_restricted: true,
    });
    expect(items.every((item) => item.ok)).toBe(true);
    expect(items.map((item) => item.text)).toEqual([
      "Negocia",
      "Sem saque",
      "Sem transferência",
      "IP restrito",
    ]);
  });

  it("flags withdrawals, transfers and a key open to any IP", () => {
    const items = permissionItems({
      can_read: true,
      can_trade: true,
      can_withdraw: true,
      can_transfer: true,
      ip_restricted: false,
    });
    expect(items.filter((item) => !item.ok).map((item) => item.text)).toEqual([
      "PODE SACAR",
      "Pode transferir",
      "Qualquer IP",
    ]);
  });
});
