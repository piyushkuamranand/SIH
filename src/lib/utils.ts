import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge multiple Tailwind class strings and handle conflicts cleanly
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format date to human-readable clinical standard (e.g. Oct 24, 2026 - 14:30)
 */
export function formatClinicalDate(date: Date | string | number): string {
  const d = typeof date === "string" || typeof date === "number" ? new Date(date) : date;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(d);
}

/**
 * Clinical vital signs threshold evaluation
 */
export function evaluateVitalStatus(
  type: "hr" | "bp_sys" | "bp_dia" | "spo2" | "temp" | "rr",
  value: number
): "normal" | "warning" | "critical" {
  switch (type) {
    case "hr": // Heart Rate (bpm)
      if (value < 50 || value > 120) return "critical";
      if (value < 60 || value > 100) return "warning";
      return "normal";
    case "bp_sys": // Systolic BP (mmHg)
      if (value < 90 || value > 160) return "critical";
      if (value > 130) return "warning";
      return "normal";
    case "bp_dia": // Diastolic BP (mmHg)
      if (value < 60 || value > 100) return "critical";
      if (value > 85) return "warning";
      return "normal";
    case "spo2": // Oxygen Saturation (%)
      if (value < 92) return "critical";
      if (value < 95) return "warning";
      return "normal";
    case "temp": // Body Temp (°C)
      if (value < 35.5 || value > 39.0) return "critical";
      if (value > 37.8) return "warning";
      return "normal";
    case "rr": // Respiratory Rate (breaths/min)
      if (value < 10 || value > 26) return "critical";
      if (value < 12 || value > 20) return "warning";
      return "normal";
    default:
      return "normal";
  }
}
