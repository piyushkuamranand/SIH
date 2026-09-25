"use client";

import React, { useEffect, useRef } from "react";
import { Cpu, Users, Stethoscope, ChevronRight, Layers, Activity } from "lucide-react";

export function LiquidGlassCard() {
  const cardRef = useRef<HTMLDivElement | null>(null);

  // Frame-sync logic for glass card mouse tilt & refractive reflection
  useEffect(() => {
    const card = cardRef.current;
    if (!card) return;

    let rafId: number;
    let targetRotateX = 0;
    let targetRotateY = 0;
    let currentRotateX = 0;
    let currentRotateY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - (rect.left + rect.width / 2);
      const y = e.clientY - (rect.top + rect.height / 2);

      targetRotateX = (-y / rect.height) * 10;
      targetRotateY = (x / rect.width) * 10;
    };

    const handleMouseLeave = () => {
      targetRotateX = 0;
      targetRotateY = 0;
    };

    window.addEventListener("mousemove", handleMouseMove);
    card.addEventListener("mouseleave", handleMouseLeave);

    const updateTilt = () => {
      currentRotateX += (targetRotateX - currentRotateX) * 0.08;
      currentRotateY += (targetRotateY - currentRotateY) * 0.08;

      if (card) {
        card.style.transform = `perspective(1000px) rotateX(${currentRotateX}deg) rotateY(${currentRotateY}deg)`;
      }

      rafId = requestAnimationFrame(updateTilt);
    };

    updateTilt();

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      if (card) card.removeEventListener("mouseleave", handleMouseLeave);
      cancelAnimationFrame(rafId);
    };
  }, []);

  return (
    <div className="relative w-full max-w-md mx-auto z-20">
      {/* Liquid Glass Container */}
      <div
        ref={cardRef}
        className="relative overflow-hidden rounded-2xl p-6 sm:p-7 backdrop-blur-xl bg-slate-900/65 border border-slate-700/60 shadow-[0_8px_32px_0_rgba(0,0,0,0.45)] text-white transition-all duration-300"
        style={{
          boxShadow: "0 8px 32px 0 rgba(0, 0, 0, 0.45), inset 0 0 0 1px rgba(255, 255, 255, 0.1)",
        }}
      >
        {/* Subtle refractive sheen layer */}
        <div className="pointer-events-none absolute -inset-[100%] opacity-20 bg-gradient-to-tr from-transparent via-cyan-400/20 to-transparent rotate-45 transform" />

        {/* Card Header with Planetary Pulse */}
        <div className="flex items-center justify-between pb-5 border-b border-slate-700/60">
          <div className="flex items-center gap-3">
            {/* Injected Planetary Pulse Effect (cyan-400 dot with animate-ping ring) */}
            <div className="relative flex h-3 w-3 items-center justify-center">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-400 shadow-[0_0_8px_#22d3ee]"></span>
            </div>

            <div>
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-cyan-300">
                Hospital Node // Active
              </span>
              <div className="text-[11px] text-slate-400 font-mono">
                Primary Cluster • Localhost 8123
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-cyan-950/60 border border-cyan-800 text-[10px] font-mono text-cyan-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Live Inference</span>
          </div>
        </div>

        {/* Main Content Blocks */}
        <div className="mt-6 space-y-4">
          {/* Block 1: AI Model Status */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-cyan-500/40 transition-colors">
            <div className="flex items-center gap-2.5 mb-1.5">
              <div className="p-1.5 rounded-md bg-cyan-500/20 text-cyan-300">
                <Cpu className="h-4 w-4" />
              </div>
              <span className="text-xs font-semibold text-slate-200">
                Inference Engine
              </span>
            </div>
            <p className="text-sm font-medium text-cyan-100">
              AI Model v2.4 Status: Online. Ready for localized inference.
            </p>
            <div className="mt-2 flex items-center gap-2 text-[11px] font-mono text-slate-400">
              <span>Latency: 18ms</span>
              <span>•</span>
              <span className="text-emerald-400">Sens: 98.4% / Spec: 97.9%</span>
            </div>
          </div>

          {/* Block 2: Clinical Queue */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-sky-500/40 transition-colors">
            <div className="flex items-center gap-2.5 mb-1.5">
              <div className="p-1.5 rounded-md bg-sky-500/20 text-sky-300">
                <Users className="h-4 w-4" />
              </div>
              <span className="text-xs font-semibold text-slate-200">
                Clinical Workflow Queue
              </span>
            </div>
            <p className="text-sm font-medium text-slate-300">
              Queue: 0 patients awaiting pre-check. 0 scans awaiting doctor review.
            </p>
            <div className="mt-2 flex items-center gap-2 text-[11px] font-mono text-slate-400">
              <span>PACS / DICOM: Synchronized</span>
            </div>
          </div>
        </div>

        {/* Footer info band */}
        <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <Stethoscope className="h-3.5 w-3.5 text-cyan-400" />
            <span className="font-mono text-[11px]">Ophthalmology Ready</span>
          </div>
          <button className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300 font-medium text-xs transition-colors">
            <span>Workstation</span>
            <ChevronRight className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
