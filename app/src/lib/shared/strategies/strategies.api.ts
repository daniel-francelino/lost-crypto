import { z } from "zod";
import { request } from "@/lib/shared/api/client";

const parameterSchema = z.object({
  name: z.string(),
  type: z.string(),
  default: z.union([z.number(), z.string(), z.boolean(), z.null()]),
  minimum: z.number().nullable(),
  description: z.string(),
});
export type StrategyParameter = z.infer<typeof parameterSchema>;

const strategySchema = z.object({
  type_key: z.string(),
  name: z.string(),
  description: z.string(),
  parameters: z.array(parameterSchema),
  parameter_count: z.number().optional(),
  too_many_parameters: z.boolean().optional(),
});
export type Strategy = z.infer<typeof strategySchema>;

export const listStrategies = (signal?: AbortSignal): Promise<Strategy[]> =>
  request({ path: "/strategies", schema: z.array(strategySchema), signal });
