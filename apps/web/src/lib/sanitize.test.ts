import { describe, expect, it } from "vitest";
import sanitizeHtml from "./sanitize";

describe("sanitizeHtml", () => {
  it("conserva el contenido del email", () => {
    const out = sanitizeHtml('<h1>Hola</h1><p>Agenda tu <a href="https://1heavy.co">demo</a></p>');
    expect(out).toContain("<h1>Hola</h1>");
    expect(out).toContain('href="https://1heavy.co"');
  });

  it.each([
    "<script>alert(1)</script>",
    "<scr<script>ipt>alert(1)</script>",
    "<script >alert(1)</script >",
    '<img src=x onerror="alert(1)">',
    '<a href="javascript:alert(1)">x</a>',
    '<iframe src="https://evil.example"></iframe>',
    '<svg onload="alert(1)"></svg>',
  ])("neutraliza %s", (payload) => {
    const out = sanitizeHtml(payload).toLowerCase();
    expect(out).not.toMatch(/<script|onerror|onload|javascript:|<iframe/);
  });
});
