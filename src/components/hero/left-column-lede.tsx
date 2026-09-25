"use client";

import React from "react";
import { ShieldCheck, Eye, Sparkles } from "lucide-react";

export function LeftColumnLede() {
  return (
    <div className="flex flex-col justify-between h-full max-w-xl z-10 text-white space-y-8">
      {/* Top Tag */}
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/20 border border-cyan-400/40 text-cyan-300">
          <Eye className="h-4 w-4 text-cyan-400" />
        </div>
        <div className="flex items-center gap-2 font-mono text-xs text-cyan-300 tracking-wider uppercase">
          <span>Phase 3 Medical AI</span>
          <span className="text-slate-500">•</span>
          <span className="text-slate-400">Class II Diagnostic</span>
        </div>
      </div>

      {/* Main Title & Lede */}
      <div className="space-y-4">
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-white leading-[1.08] drop-shadow-sm">
          OcuScan AI<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-sky-300 to-blue-500">
            Clinical Retinal Suite
          </span>
        </h1>

        <p className="text-slate-300 text-base sm:text-lg leading-relaxed font-normal max-w-lg">
          Enterprise diagnostic pipeline for Diabetic Retinopathy. Integrating real-time computer vision with ophthalmology workflows.
        </p>
      </div>

      {/* Chamfered Button: "System Secure" with Shield icon */}
      <div className="pt-2 flex flex-wrap items-center gap-4">
        <button
          type="button"
          className="relative group inline-flex items-center gap-2.5 px-6 py-3.5 bg-gradient-to-r from-cyan-500 to-sky-600 hover:from-cyan-400 hover:to-sky-500 text-slate-950 font-bold text-sm uppercase tracking-wider transition-all duration-200 shadow-[0_0_20px_rgba(34,211,238,0.3)] hover:shadow-[0_0_30px_rgba(34,211,238,0.5)] active:scale-[0.98] cursor-pointer"
          style={{
            clipPath:
              "polygon(12px 0%, 100% 0%, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0% 100%, 0% 12px)",
          }}
        >
          <ShieldCheck className="h-5 w-5 text-slate-950 stroke-[2.4]" />
          <span>System Secure</span>
        </button>

        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400"></span>
          <span>HIPAA & SOC2 Validated</span>
        </div>
      </div>
    </div>
  );
}
