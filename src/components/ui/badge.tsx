import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-wide transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "bg-slate-100 text-slate-800 border border-slate-200",
        slate: "bg-slate-100 text-slate-700 border border-slate-200",
        cyan: "bg-cyan-50 text-cyan-700 border border-cyan-200",
        blue: "bg-sky-50 text-sky-700 border border-sky-200",
        success: "bg-emerald-50 text-emerald-700 border border-emerald-200",
        warning: "bg-amber-50 text-amber-700 border border-amber-200",
        danger: "bg-rose-50 text-rose-700 border border-rose-200",
        critical: "bg-rose-600 text-white animate-pulse",
        outline: "text-slate-600 border border-slate-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean;
  dotColor?: "emerald" | "amber" | "rose" | "cyan" | "slate";
}

function Badge({ className, variant, dot, dotColor = "cyan", children, ...props }: BadgeProps) {
  const dotColorClasses = {
    emerald: "bg-emerald-500",
    amber: "bg-amber-500",
    rose: "bg-rose-500",
    cyan: "bg-cyan-500",
    slate: "bg-slate-500",
  };

  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && (
        <span className={cn("h-1.5 w-1.5 rounded-full", dotColorClasses[dotColor])} />
      )}
      {children}
    </div>
  );
}

export { Badge, badgeVariants };
