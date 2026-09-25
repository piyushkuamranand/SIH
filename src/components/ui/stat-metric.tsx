import * as React from "react";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface StatMetricProps {
  label: string;
  value: string | number;
  unit?: string;
  icon?: LucideIcon;
  trend?: {
    value: string;
    direction: "up" | "down" | "stable";
    label?: string;
  };
  status?: "normal" | "warning" | "critical" | "highlight";
  subtext?: string;
  className?: string;
}

export function StatMetric({
  label,
  value,
  unit,
  icon: Icon,
  trend,
  status = "normal",
  subtext,
  className,
}: StatMetricProps) {
  const statusStyles = {
    normal: "border-slate-200/80 bg-white",
    highlight: "border-cyan-200 bg-cyan-50/30 text-cyan-950",
    warning: "border-amber-200 bg-amber-50/30 text-amber-950",
    critical: "border-rose-200 bg-rose-50/40 text-rose-950",
  };

  const iconBgStyles = {
    normal: "bg-slate-100 text-slate-700",
    highlight: "bg-cyan-100 text-cyan-700",
    warning: "bg-amber-100 text-amber-700",
    critical: "bg-rose-100 text-rose-700",
  };

  return (
    <div
      className={cn(
        "flex flex-col p-4 rounded-xl border shadow-xs transition-all",
        statusStyles[status],
        className
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-500">{label}</span>
        {Icon && (
          <div className={cn("p-1.5 rounded-md", iconBgStyles[status])}>
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-1.5">
        <span className="text-2xl font-bold tracking-tight text-slate-900 font-mono">
          {value}
        </span>
        {unit && <span className="text-xs font-semibold text-slate-500">{unit}</span>}
      </div>

      {(trend || subtext) && (
        <div className="mt-2 flex items-center gap-1.5 text-xs">
          {trend && (
            <span
              className={cn(
                "font-semibold",
                trend.direction === "up" && "text-rose-600",
                trend.direction === "down" && "text-emerald-600",
                trend.direction === "stable" && "text-slate-500"
              )}
            >
              {trend.direction === "up" ? "↑" : trend.direction === "down" ? "↓" : "→"}{" "}
              {trend.value}
            </span>
          )}
          {subtext && <span className="text-slate-500 truncate">{subtext}</span>}
        </div>
      )}
    </div>
  );
}
