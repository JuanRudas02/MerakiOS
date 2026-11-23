import { describe, expect, it, vi } from "vitest";
import { ApiError, buildUrl, onUnauthorized, request, setAuthToken, toApiError } from "./client";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("toApiError", () => {
  it("mapea el formato de error del backend", async () => {
    const err = await toApiError(json(409, { error: { code: "email_taken", message: "Ya existe una cuenta con ese email" } }));
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(409);
    expect(err.code).toBe("email_taken");
    expect(err.message).toBe("Ya existe una cuenta con ese email");
  });

  it("mapea errores de validación de FastAPI", async () => {
    const err = await toApiError(json(422, { detail: [{ loc: ["body", "email"], msg: "value is not a valid email" }] }));
    expect(err.code).toBe("validation_error");
    expect(err.message).toBe("email: value is not a valid email");
  });

  it("usa un mensaje por defecto si el cuerpo no es JSON", async () => {
    const err = await toApiError(new Response("boom", { status: 502 }));
    expect(err.code).toBe("http_502");
    expect(err.message).toMatch(/proveedor externo/);
  });
});

describe("request", () => {
  it("envía el bearer token y serializa query params", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(200, { ok: true }));
    setAuthToken("tkn");
    await request("GET", "/crm/contacts", { query: { q: "ana", stage: undefined, page: 2 } });
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe(buildUrl("/crm/contacts", { q: "ana", page: 2 }));
    expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer tkn");
    setAuthToken(null);
  });

  it("invoca el handler de sesión expirada en 401", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json(401, { error: { code: "authentication_failed", message: "Token inválido" } }));
    const handler = vi.fn();
    setAuthToken("expired");
    onUnauthorized(handler);
    await expect(request("GET", "/auth/me")).rejects.toMatchObject({ status: 401, code: "authentication_failed" });
    expect(handler).toHaveBeenCalledOnce();
    onUnauthorized(null);
    setAuthToken(null);
  });

  it("convierte fallas de red en ApiError network_error", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(request("GET", "/health")).rejects.toMatchObject({ status: 0, code: "network_error" });
  });
});
