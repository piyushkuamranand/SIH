import React from "react";
import Link from "next/link";
import { Upload, Stethoscope, ArrowRight, LayoutDashboard, Sparkles, CheckCircle2 } from "lucide-react";

export function RolesSection() {
  return (
    <section className="roles-section bg-[#0f172a] text-white py-24 px-6 relative z-10 border-t border-slate-800">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-400/30 text-cyan-300 text-xs font-mono">
            <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
            <span>Role-Based Clinical Access</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
            Select Your Clinical Workspace
          </h2>
          <p className="text-slate-400 text-sm sm:text-base">
            Enterprise diagnostics pipeline with specialized interfaces for image acquisition technicians and attending ophthalmologists.
          </p>
        </div>

        {/* 2-Column Role Selection Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          {/* Card 1: Technician Workspace */}
          <Link
            href="/login.html"
            className="group relative rounded-2xl p-8 bg-slate-900/90 border border-slate-800 hover:border-cyan-500/80 shadow-xl hover:shadow-[0_0_35px_rgba(6,182,212,0.25)] transition-all duration-300 transform hover:-translate-y-1.5 flex flex-col justify-between overflow-hidden cursor-pointer"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/10 rounded-bl-full pointer-events-none group-hover:bg-cyan-500/20 transition-all duration-300"></div>

            <div>
              <div className="flex items-center justify-between mb-6">
                <div className="h-14 w-14 rounded-2xl bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center text-cyan-400 group-hover:scale-110 transition-transform duration-300 shadow-md">
                  <Upload className="h-7 w-7 stroke-[2.2]" />
                </div>
                <span className="font-mono text-xs font-bold px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-800 text-cyan-300">
                  Phase 1 & 2 Ingest
                </span>
              </div>

              <h3 className="text-2xl font-bold text-white group-hover:text-cyan-300 transition-colors">
                Technician Workspace
              </h3>
              <p className="text-sm font-semibold text-cyan-400 mt-1">
                Upload &amp; Pre-check
              </p>
              <p className="text-slate-400 text-xs sm:text-sm mt-3 leading-relaxed">
                Ingest high-resolution fundus scans, validate DICOM tags, and run automated Phase 1 AI image quality checks (blur &amp; exposure validation) before routing.
              </p>

              <div className="mt-6 space-y-2 border-t border-slate-800/80 pt-4 text-xs text-slate-300">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Drag &amp; Drop Retinal Upload (PNG/JPG/TIFF/DCM)</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Real-time blur and lighting exposure scoring</span>
                </div>
              </div>
            </div>

            <div className="mt-8 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs font-bold uppercase tracking-wider text-cyan-400 group-hover:text-cyan-300">
              <span>Launch Upload Portal</span>
              <ArrowRight className="h-4 w-4 transform group-hover:translate-x-1.5 transition-transform" />
            </div>
          </Link>

          {/* Card 2: Ophthalmologist Workstation */}
          <Link
            href="/login.html"
            className="group relative rounded-2xl p-8 bg-slate-900/90 border border-slate-800 hover:border-amber-500/80 shadow-xl hover:shadow-[0_0_35px_rgba(251,191,36,0.22)] transition-all duration-300 transform hover:-translate-y-1.5 flex flex-col justify-between overflow-hidden cursor-pointer"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/10 rounded-bl-full pointer-events-none group-hover:bg-amber-500/20 transition-all duration-300"></div>

            <div>
              <div className="flex items-center justify-between mb-6">
                <div className="h-14 w-14 rounded-2xl bg-amber-500/20 border border-amber-400/40 flex items-center justify-center text-amber-400 group-hover:scale-110 transition-transform duration-300 shadow-md">
                  <Stethoscope className="h-7 w-7 stroke-[2.2]" />
                </div>
                <span className="font-mono text-xs font-bold px-3 py-1 rounded-full bg-amber-950/80 border border-amber-800 text-amber-300">
                  Phase 3 Diagnostics
                </span>
              </div>

              <h3 className="text-2xl font-bold text-white group-hover:text-amber-300 transition-colors">
                Ophthalmologist Workstation
              </h3>
              <p className="text-sm font-semibold text-amber-400 mt-1">
                Review Heatmaps &amp; Approve
              </p>
              <p className="text-slate-400 text-xs sm:text-sm mt-3 leading-relaxed">
                High-contrast radiology reading environment. Review AI Grad-CAM saliency heatmaps, microaneurysm bounding boxes, and execute 30-second grading decisions with hotkeys.
              </p>

              <div className="mt-6 space-y-2 border-t border-slate-800/80 pt-4 text-xs text-slate-300">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-amber-400" />
                  <span>Multi-layer toggles (Base, Grad-CAM, Lesion Boxes)</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-amber-400" />
                  <span>Rapid hotkey decisions ([A] Approve, [M] Modify)</span>
                </div>
              </div>
            </div>

            <div className="mt-8 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs font-bold uppercase tracking-wider text-amber-400 group-hover:text-amber-300">
              <span>Launch Workstation</span>
              <ArrowRight className="h-4 w-4 transform group-hover:translate-x-1.5 transition-transform" />
            </div>
          </Link>

        </div>

        {/* Card 3: Central Queue & Flow Dashboard Link */}
        <div className="mt-8 flex justify-center">
          <Link
            href="/login.html"
            className="group relative w-full max-w-2xl flex items-center gap-5 p-5 sm:p-6 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-cyan-500/50 shadow-xl hover:shadow-[0_0_30px_rgba(6,182,212,0.18)] transition-all duration-300 transform hover:-translate-y-1"
          >
            <div className="h-12 w-12 rounded-xl bg-cyan-500/15 border border-cyan-400/30 flex items-center justify-center text-cyan-400 group-hover:scale-110 transition-transform duration-300 shrink-0">
              <LayoutDashboard className="h-6 w-6 stroke-[2.2]" />
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2.5 flex-wrap">
                <h4 className="text-base sm:text-lg font-bold text-white group-hover:text-cyan-300 transition-colors">
                  View Central Queue &amp; Flow Dashboard
                </h4>
                <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 uppercase">
                  Live Kanban
                </span>
              </div>
              <p className="text-slate-400 text-xs sm:text-sm mt-0.5 line-clamp-1">
                Hospital diagnostic pipeline · Drag &amp; drop patient triage · Real-time PACS audit log &amp; sign-off tracking
              </p>
            </div>

            <ArrowRight className="h-5 w-5 text-cyan-400 transform group-hover:translate-x-1.5 transition-transform shrink-0" />
          </Link>
        </div>

      </div>
    </section>
  );
}
