import * as React from "react";

import { cn } from "@/lib/utils";

export interface InputProps extends React.ComponentProps<"input"> {
  variant?: "dark" | "light";
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, variant = "dark", ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-12 w-full rounded-lg border px-4 py-3 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-300",
          variant === "dark" 
            ? "bg-muted/50 border-border text-foreground focus:border-meraki-blue focus:bg-muted/70" 
            : "bg-meraki-white border-meraki-blue/20 text-meraki-black focus:border-meraki-blue focus:ring-meraki-blue/20",
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

export { Input };
