import { request } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";
import { emptySchema } from "@/lib/shared/api/schemas";
import { connectionSchema } from "@/lib/shared/exchanges/connections.api";

export type ConnectionInput = {
  exchange: string;
  environment: string;
  confirm_real_money: boolean;
  label: string;
  api_key: string;
  api_secret: string;
};

export const createConnection = (body: ConnectionInput) =>
  request({
    method: HttpMethod.Post,
    path: "/exchange-connections",
    schema: connectionSchema,
    body,
  });

export const disableConnection = (id: string) =>
  request({
    method: HttpMethod.Post,
    path: `/exchange-connections/${id}/disable`,
    schema: emptySchema,
  });
