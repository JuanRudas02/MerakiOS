import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

/**
 * Aparición sutil al montar. No depende de IntersectionObserver para que el
 * contenido nunca quede oculto (crawlers, impresión, capturas). Se desactiva con
 * prefers-reduced-motion.
 */
export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: Math.min(delay, 0.3), ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
