/**
 * Cliente HTTP tipado de 1heavy (fetch nativo, sin dependencias).
 *
 * - Base URL: VITE_API_URL (por defecto http://localhost:8000/api/v1).
 * - Inyecta el bearer token de la sesión.
 * - Traduce el formato de error del backend `{ error: { code, message } }` a `ApiError`.
 */

export const API_URL: string = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000/api/v1";

/** Origen del API (para resolver URLs relativas como `/storage/...`). */
export const API_ORIGIN = (() => {
  try {
    return new URL(API_URL).origin;
  } catch {
    return "";
  }
})();

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }

  get isUnauthorized() {
    return this.status === 401;
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

export interface RequestOptions {
  query?: Query;
  body?: unknown;
  form?: FormData;
  signal?: AbortSignal;
  auth?: boolean;
}

let authToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

export function onUnauthorized(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

export function buildUrl(path: string, query?: Query): string {
  const url = `${API_URL.replace(/\/$/, "")}${path.startsWith("/") ? path : `/${path}`}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

const FALLBACK_MESSAGES: Record<number, string> = {
  400: "Solicitud inválida",
  401: "Tu sesión expiró. Inicia sesión de nuevo.",
  403: "No tienes permiso para esta acción",
  404: "Recurso no encontrado",
  409: "Conflicto con el estado actual",
  422: "Datos inválidos",
  429: "Demasiados intentos, espera un momento",
  502: "Un proveedor externo no respondió",
};

/** Convierte cualquier respuesta de error del backend (o de FastAPI) en ApiError. */
export async function toApiError(response: Response): Promise<ApiError> {
  let code = `http_${response.status}`;
  let message = FALLBACK_MESSAGES[response.status] ?? "Error inesperado";
  try {
    const data = await response.json();
    if (data?.error?.message) {
      code = data.error.code ?? code;
      message = data.error.message;
    } else if (typeof data?.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data?.detail) && data.detail[0]?.msg) {
      code = "validation_error";
      const loc = (data.detail[0].loc ?? []).slice(1).join(".");
      message = loc ? `${loc}: ${data.detail[0].msg}` : data.detail[0].msg;
    }
  } catch {
    /* cuerpo no JSON */
  }
  return new ApiError(response.status, code, message);
}

export async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  if (options.auth !== false && authToken) headers.Authorization = `Bearer ${authToken}`;

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), { method, headers, body, signal: options.signal });
  } catch (err) {
    if ((err as Error)?.name === "AbortError") throw err;
    throw new ApiError(0, "network_error", "No pudimos conectar con el servidor de 1heavy");
  }

  if (!response.ok) {
    const error = await toApiError(response);
    if (error.isUnauthorized && authToken && unauthorizedHandler) unauthorizedHandler();
    throw error;
  }
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const http = {
  get: <T>(path: string, query?: Query, signal?: AbortSignal) => request<T>("GET", path, { query, signal }),
  post: <T>(path: string, body?: unknown, query?: Query) => request<T>("POST", path, { body, query }),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, { body }),
  del: <T>(path: string) => request<T>("DELETE", path),
  upload: <T>(path: string, form: FormData) => request<T>("POST", path, { form }),
  public: {
    get: <T>(path: string, query?: Query) => request<T>("GET", path, { query, auth: false }),
    post: <T>(path: string, body?: unknown) => request<T>("POST", path, { body, auth: false }),
  },
};

/** Resuelve una URL de archivo devuelta por el API (`/storage/...`). */
export function fileUrl(url: string): string {
  return url.startsWith("http") ? url : `${API_ORIGIN}${url}`;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}
