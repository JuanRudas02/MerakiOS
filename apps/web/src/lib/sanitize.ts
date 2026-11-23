/**
 * Saneamiento mínimo del HTML generado por IA antes de previsualizarlo.
 * La vista previa además corre en un <iframe sandbox=""> (sin scripts ni same-origin),
 * así que esto es defensa en profundidad.
 */
export default function sanitizeHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/<(iframe|object|embed)[\s\S]*?>[\s\S]*?<\/\1>/gi, "")
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/(href|src)\s*=\s*(["'])\s*javascript:[^"']*\2/gi, '$1="#"');
}
