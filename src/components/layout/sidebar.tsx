"use client";

import * as React from "react";
import Link from "next/link";
import {
  Activity,
  HeartPulse,
  Users,
  FlaskConical,
  Pill,
  FileText,
  Settings,
  LayoutDashboard,
  ShieldAlert,
  Stethoscope,
  ChevronRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

const navItems = [
  { id: "overview", label: "Ward Overview", icon: LayoutDashboard, href: "/", active: true },
  { id: "patients", label: "Patient Roster", icon: Users, href: "#", count: "28 Active" },
  { id: "triage", label: "Acuity & Triage", icon: Activity, href: "#", badge: "2 Urgent", badgeVariant: "danger" as const },
  { id: "vitals", label: "Live Telemetry", icon: HeartPulse, href: "#" },
  { id: "labs", label: "Lab Diagnostic Panels", icon: FlaskConical, href: "#", count: "5 New" },
  { id: "medications", label: "e-Prescriptions (Rx)", icon: Pill, href: "#" },
  { id: "records", label: "Clinical EMR Notes", icon: FileText, href: "#" },
];

export function ClinicalSidebar() {
  return (
    <aside className="w-64 border-r border-slate-200 bg-white flex flex-col justify-between shrink-0 h-screen sticky top-0 select-none">
      {/* Brand Header */}
      <div>
        <div className="h-16 flex items-center gap-3 px-5 border-b border-slate-100 bg-slate-900 text-white">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500 text-slate-950 font-bold shadow-sm">
            <Stethoscope className="h-5 w-5 text-slate-950 stroke-[2.2]" />
          </div>
          <div>
            <div className="flex items-center gap-1.5 font-bold text-sm tracking-tight text-white">
              <span>AURA CLINICAL</span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-semibold">
                v2.4
              </span>
            </div>
            <div className="text-[11px] text-slate-400 font-medium">Intensive Care & ER Portal</div>
          </div>
        </div>

        {/* Navigation Sections */}
        <div className="p-3 space-y-6">
          <div>
            <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Clinical Workflows
            </div>
            <nav className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.id}
                    href={item.href}
                    className={`flex items-center justify-between px-3 py-2 text-xs font-medium rounded-lg transition-colors group ${
                      item.active
                        ? "bg-cyan-50 text-cyan-900 font-semibold"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon
                        className={`h-4 w-4 transition-colors ${
                          item.active ? "text-cyan-600 stroke-[2.2]" : "text-slate-400 group-hover:text-slate-600"
                        }`}
                      />
                      <span>{item.label}</span>
                    </div>

                    {item.badge && (
                      <Badge variant={item.badgeVariant || "cyan"} className="text-[10px] px-1.5 py-0">
                        {item.badge}
                      </Badge>
                    )}

                    {item.count && (
                      <span className="text-[11px] text-slate-400 font-mono">
                        {item.count}
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div>
            <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Monitoring & Safety
            </div>
            <nav className="space-y-1">
              <a
                href="#"
                className="flex items-center justify-between px-3 py-2 text-xs font-medium text-slate-600 rounded-lg hover:bg-slate-50 hover:text-slate-900"
              >
                <div className="flex items-center gap-2.5">
                  <ShieldAlert className="h-4 w-4 text-amber-500" />
                  <span>Clinical Risk & Fall Safety</span>
                </div>
                <ChevronRight className="h-3 w-3 text-slate-400" />
              </a>
              <a
                href="#"
                className="flex items-center justify-between px-3 py-2 text-xs font-medium text-slate-600 rounded-lg hover:bg-slate-50 hover:text-slate-900"
              >
                <div className="flex items-center gap-2.5">
                  <Settings className="h-4 w-4 text-slate-400" />
                  <span>Telemetry Devices</span>
                </div>
              </a>
            </nav>
          </div>
        </div>
      </div>

      {/* Ward Status Footnote */}
      <div className="p-3 border-t border-slate-100 bg-slate-50/70 m-3 rounded-xl border">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-[11px] font-semibold text-slate-800">ICU Ward 4-East</span>
          </div>
          <span className="text-[10px] font-mono text-slate-500">Occupancy: 88%</span>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
          <div className="bg-cyan-500 h-1.5 rounded-full" style={{ width: "88%" }}></div>
        </div>
        <p className="text-[10px] text-slate-500 mt-2">
          Sync status: Telemetry stream connected
        </p>
      </div>
    </aside>
  );
}
