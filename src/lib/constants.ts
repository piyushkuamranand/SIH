export const CLINICAL_THEME = {
  primary: "cyan",
  secondary: "blue",
  neutral: "slate",
  success: "emerald",
  warning: "amber",
  danger: "rose",
} as const;

export const TRIAGE_LEVELS = {
  LEVEL_1_RESUSCITATION: { code: 1, label: "Immediate (Resuscitation)", color: "rose" },
  LEVEL_2_EMERGENT: { code: 2, label: "Emergent", color: "orange" },
  LEVEL_3_URGENT: { code: 3, label: "Urgent", color: "amber" },
  LEVEL_4_LESS_URGENT: { code: 4, label: "Semi-Urgent", color: "cyan" },
  LEVEL_5_NON_URGENT: { code: 5, label: "Non-Urgent", color: "slate" },
} as const;

export const CLINICAL_NAV_ITEMS = [
  { id: "overview", label: "Ward Overview", icon: "LayoutDashboard", href: "/" },
  { id: "patients", label: "Active Patients", icon: "Users", href: "/patients", count: 24 },
  { id: "triage", label: "Triage & Queue", icon: "Activity", href: "/triage", badge: "3 Urgent" },
  { id: "vitals", label: "Telemetry & Vitals", icon: "HeartPulse", href: "/vitals" },
  { id: "labs", label: "Lab Diagnostic Panels", icon: "FlaskConical", href: "/labs", count: 8 },
  { id: "medications", label: "e-Prescribing & Rx", icon: "Pill", href: "/medications" },
  { id: "records", label: "Clinical Records (EMR)", icon: "FileText", href: "/records" },
  { id: "settings", label: "System & Devices", icon: "Settings", href: "/settings" },
] as const;
