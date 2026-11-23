import DOMPurify from "dompurify";

/**
 * Sanea el HTML generado por IA antes de previsualizarlo.
 *
 * Usa DOMPurify (parser real del navegador, no expresiones regulares) con un
 * perfil sólo-HTML: elimina scripts, iframes, formularios, manejadores `on*` y
 * URLs `javascript:`. La vista previa además corre en un `<iframe sandbox="">`
 * y el backend aplica su propio saneamiento: defensa en profundidad.
 */
export default function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["style", "form", "input", "button", "iframe", "object", "embed"],
    FORBID_ATTR: ["style"],
  });
}
