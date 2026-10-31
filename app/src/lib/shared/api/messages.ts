import { ApiError, ApiErrorKind, HttpStatus } from "@/lib/shared/api/api-error";

export const GENERIC_ERROR = "Algo deu errado. Tente novamente.";
export const NETWORK_ERROR = "Não foi possível falar com o servidor. Verifique sua conexão.";
export const FORBIDDEN_ERROR = "Você não tem permissão para fazer isso.";
export const NOT_FOUND_ERROR = "Não encontrado.";
export const UNAVAILABLE_ERROR = "O servidor não está configurado para isso.";
export const CONFLICT_ERROR = "O estado mudou. Atualize a tela e tente de novo.";

export const errorMessage = (error: unknown): string => {
  if (!(error instanceof ApiError)) return GENERIC_ERROR;
  if (error.kind === ApiErrorKind.Network) return NETWORK_ERROR;
  if (error.kind === ApiErrorKind.InvalidResponse) return GENERIC_ERROR;
  if (error.hasStatus(HttpStatus.Forbidden)) return FORBIDDEN_ERROR;
  if (error.hasStatus(HttpStatus.NotFound)) return NOT_FOUND_ERROR;
  if (error.hasStatus(HttpStatus.Unavailable)) return UNAVAILABLE_ERROR;
  if (error.hasStatus(HttpStatus.Conflict)) {
    return error.detail === "" ? CONFLICT_ERROR : error.detail;
  }
  return error.detail === "" ? GENERIC_ERROR : error.detail;
};

export const refusalMessage = (error: unknown): string => {
  if (error instanceof ApiError && error.kind === ApiErrorKind.Http && error.detail !== "") {
    return error.detail;
  }
  return errorMessage(error);
};
