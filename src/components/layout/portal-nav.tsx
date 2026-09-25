"use client";

import React from "react";
import { Eye, Shield, Activity } from "lucide-react";
import { SlideMenu } from "@/components/layout/slide-menu";

export function PortalNav() {
  return (
    <header className="relative z-30 flex items-center justify-between px-6 py-5 max-w-7xl mx-auto w-full">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-cyan-400 to-sky-600 flex items-center justify-center text-slate-950 font-extrabold shadow-[0_0_15px_rgba(34,211,238,0.4)]">
          <Eye className="h-6 w-6 stroke-[2.4]" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-extrabold text-base tracking-tight text-white">
              OCUSCAN<span className="text-cyan-400">.AI</span>
            </span>
            <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-400/30">
              PHASE 3
            </span>
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            Retinal Diagnostic Node #8123
          </div>
        </div>
      </div>

      {/* Center status indicator */}
      <div className="hidden md:flex items-center gap-3 px-3.5 py-1.5 rounded-full bg-slate-900/80 border border-slate-700/80 backdrop-blur-md">
        <div className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </div>
        <span className="text-xs font-mono text-slate-300">
          Neural Pipeline: <span className="text-cyan-300 font-bold">Synchronized</span>
        </span>
      </div>

      {/* Right Slide-in Menu trigger */}
      <div className="flex items-center gap-3">
        <SlideMenu />
      </div>
    </header>
  );
}
