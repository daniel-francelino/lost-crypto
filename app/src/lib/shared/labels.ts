import {
  BotState,
  ConnectionStatus,
  Environment,
  ExecutionMode,
  JobStatus,
  OrderStatus,
  Role,
  Side,
  SignalKind,
  Unknown,
} from "@/lib/shared/enums";

const UNKNOWN_LABEL = "Desconhecido";

const pick = (labels: Record<string, string>, value: string): string =>
  labels[value] ?? UNKNOWN_LABEL;

export const botStateLabel = (value: string): string =>
  pick(
    {
      [BotState.Stopped]: "Parado",
      [BotState.Running]: "Rodando",
      [BotState.Paused]: "Pausado",
      [BotState.Error]: "Erro",
      [Unknown]: UNKNOWN_LABEL,
    },
    value,
  );

export const modeLabel = (value: string): string =>
  pick(
    {
      [ExecutionMode.Paper]: "PAPER",
      [ExecutionMode.Testnet]: "TESTNET",
      [ExecutionMode.Live]: "LIVE",
    },
    value,
  );

export const environmentLabel = (value: string): string =>
  pick({ [Environment.Testnet]: "TESTNET", [Environment.Live]: "LIVE" }, value);

export const orderStatusLabel = (value: string): string =>
  pick(
    {
      [OrderStatus.Intent]: "Intenção",
      [OrderStatus.Submitting]: "Enviando",
      [OrderStatus.Open]: "Aberta",
      [OrderStatus.PartiallyFilled]: "Parcialmente executada",
      [OrderStatus.Filled]: "Executada",
      [OrderStatus.Canceled]: "Cancelada",
      [OrderStatus.Rejected]: "Rejeitada",
      [OrderStatus.Expired]: "Expirada",
      [OrderStatus.Unknown]: "Resultado incerto",
    },
    value,
  );

export const jobStatusLabel = (value: string): string =>
  pick(
    {
      [JobStatus.Queued]: "Na fila",
      [JobStatus.Running]: "Executando",
      [JobStatus.Completed]: "Concluído",
      [JobStatus.Failed]: "Falhou",
    },
    value,
  );

export const connectionStatusLabel = (value: string): string =>
  pick(
    {
      [ConnectionStatus.Pending]: "Aguardando verificação",
      [ConnectionStatus.Active]: "Ativa",
      [ConnectionStatus.Invalid]: "Inválida",
      [ConnectionStatus.Disabled]: "Desativada",
    },
    value,
  );

export const sideLabel = (value: string): string =>
  pick({ [Side.Buy]: "Compra", [Side.Sell]: "Venda" }, value);

export const signalKindLabel = (value: string): string =>
  pick({ [SignalKind.Entry]: "Entrada", [SignalKind.Exit]: "Saída" }, value);

export const roleLabel = (value: string): string =>
  pick({ [Role.Admin]: "Administrador", [Role.Viewer]: "Somente leitura" }, value);

export const CONNECTION_STATUS_HELP: Record<string, string> = {
  [ConnectionStatus.Pending]:
    "O worker ainda vai verificar o que esta chave pode fazer. Chaves live só ficam ativas se forem somente de trade, sem saque nem transferência, e restritas por IP.",
  [ConnectionStatus.Active]: "Chave verificada e pronta para uso.",
  [ConnectionStatus.Invalid]:
    "A chave foi recusada ou tem permissões perigosas. Crie uma nova chave mais restrita e desative esta.",
  [ConnectionStatus.Disabled]: "Esta conexão foi desativada e não é mais usada.",
};
