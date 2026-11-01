export const BotTab = {
  Summary: "resumo",
  Orders: "ordens",
  Signals: "sinais",
  Performance: "desempenho",
  Parity: "paridade",
  Diagnosis: "diagnostico",
  Config: "configuracao",
  Audit: "auditoria",
} as const;
export type BotTab = (typeof BotTab)[keyof typeof BotTab];

export const BOT_TAB_LABELS: Record<BotTab, string> = {
  [BotTab.Summary]: "Resumo",
  [BotTab.Orders]: "Ordens",
  [BotTab.Signals]: "Sinais",
  [BotTab.Performance]: "Desempenho",
  [BotTab.Parity]: "Paridade",
  [BotTab.Diagnosis]: "Diagnóstico",
  [BotTab.Config]: "Configuração",
  [BotTab.Audit]: "Auditoria",
};
