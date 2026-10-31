import { JobStatus } from "@/lib/shared/enums";

export const Poll = {
  Status: 5_000,
  Overview: 10_000,
  Detail: 5_000,
  Fast: 2_000,
  Slow: 30_000,
  Connections: 10_000,
} as const;

export const isJobFinished = (status: string | undefined): boolean =>
  status === JobStatus.Completed || status === JobStatus.Failed;

export const pollWhile = (active: boolean, interval: number): number | false =>
  active ? interval : false;
