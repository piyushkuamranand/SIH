"use client";

import * as React from "react";
import { Patient } from "@/types/clinical";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Heart, Activity, Wind, Thermometer, Radio, Zap } from "lucide-react";

interface LiveTelemetryPanelProps {
  patient: Patient;
}

export function LiveTelemetryPanel({ patient }: LiveTelemetryPanelProps) {
  const { currentVitals } = patient;

  return (
    <Card className="border-slate-200 bg-slate-900 text-white shadow-md overflow-hidden">
      {/* Header telemetry band */}
      <div className="flex items-center justify-between px-5 py-3.5 bg-slate-950 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Radio className="h-4 w-4 text-cyan-400 animate-pulse" />
            <span className="font-mono text-xs font-bold text-cyan-300 uppercase tracking-wider">
              Bed {patient.bedNumber} • Telemetry Stream (Lead II)
            </span>
          </div>
          <Badge variant="cyan" className="bg-cyan-950/80 border-cyan-800 text-cyan-300 text-[10px]">
            {patient.fullName} (MRN: {patient.mrn})
          </Badge>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <span>Filter: 0.05-40Hz</span>
          <span>•</span>
          <span className="text-emerald-400 font-semibold">ST-Seg Normal</span>
        </div>
      </div>

      <CardContent className="p-5">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Simulated Lead II ECG Waveform display */}
          <div className="lg:col-span-3 flex flex-col justify-between rounded-lg bg-slate-950/80 border border-slate-800/80 p-3 h-44 relative overflow-hidden">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 z-10">
              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                ECG Lead II
              </span>
              <span>25 mm/s • 10 mm/mV</span>
            </div>

            {/* SVG ECG Waveform */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-80">
              <svg
                className="w-full h-24 text-emerald-400 stroke-current"
                viewBox="0 0 600 100"
                fill="none"
                preserveAspectRatio="none"
              >
                <path
                  d="M0 50 L50 50 L60 48 L70 50 L80 50 L85 53 L90 15 L95 85 L100 45 L105 52 L115 50 L130 50 L145 42 L160 50 L200 50 L250 50 L260 48 L270 50 L280 50 L285 53 L290 15 L295 85 L300 45 L305 52 L315 50 L330 50 L345 42 L360 50 L400 50 L450 50 L460 48 L470 50 L480 50 L485 53 L490 15 L495 85 L500 45 L505 52 L515 50 L530 50 L545 42 L560 50 L600 50"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>

            {/* Pleth / SpO2 Waveform */}
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 z-10 pt-6">
              <span className="text-cyan-400 font-semibold flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400"></span>
                Pleth Wave (SpO₂)
              </span>
              <span className="text-cyan-400/80 font-mono">PI: 4.8%</span>
            </div>
          </div>

          {/* Key vital digital numerical meters */}
          <div className="grid grid-cols-2 gap-2.5">
            {/* HR */}
            <div className="bg-slate-950/90 border border-slate-800 rounded-lg p-3 flex flex-col justify-between">
              <div className="flex items-center justify-between text-[11px] text-emerald-400 font-bold uppercase tracking-wider">
                <span className="flex items-center gap-1">
                  <Heart className="h-3.5 w-3.5 fill-emerald-500/20" /> HR
                </span>
                <span className="text-slate-500 font-normal">bpm</span>
              </div>
              <div className="text-3xl font-mono font-bold text-emerald-400 mt-1">
                {currentVitals.heartRate}
              </div>
              <div className="text-[10px] text-slate-500 font-mono">Limits: 50 - 120</div>
            </div>

            {/* SpO2 */}
            <div className="bg-slate-950/90 border border-slate-800 rounded-lg p-3 flex flex-col justify-between">
              <div className="flex items-center justify-between text-[11px] text-cyan-400 font-bold uppercase tracking-wider">
                <span className="flex items-center gap-1">
                  <Wind className="h-3.5 w-3.5" /> SpO₂
                </span>
                <span className="text-slate-500 font-normal">%</span>
              </div>
              <div className="text-3xl font-mono font-bold text-cyan-400 mt-1">
                {currentVitals.oxygenSaturation}
              </div>
              <div className="text-[10px] text-slate-500 font-mono">Limits: 92 - 100</div>
            </div>

            {/* NIBP */}
            <div className="bg-slate-950/90 border border-slate-800 rounded-lg p-3 flex flex-col justify-between">
              <div className="flex items-center justify-between text-[11px] text-amber-400 font-bold uppercase tracking-wider">
                <span className="flex items-center gap-1">
                  <Activity className="h-3.5 w-3.5" /> NIBP
                </span>
                <span className="text-slate-500 font-normal">mmHg</span>
              </div>
              <div className="text-xl font-mono font-bold text-amber-400 mt-1">
                {currentVitals.bloodPressureSystolic}/{currentVitals.bloodPressureDiastolic}
              </div>
              <div className="text-[10px] text-slate-500 font-mono">MAP: 92</div>
            </div>

            {/* Resp Rate */}
            <div className="bg-slate-950/90 border border-slate-800 rounded-lg p-3 flex flex-col justify-between">
              <div className="flex items-center justify-between text-[11px] text-sky-400 font-bold uppercase tracking-wider">
                <span className="flex items-center gap-1">
                  <Activity className="h-3.5 w-3.5" /> Resp
                </span>
                <span className="text-slate-500 font-normal">/min</span>
              </div>
              <div className="text-2xl font-mono font-bold text-sky-400 mt-1">
                {currentVitals.respiratoryRate}
              </div>
              <div className="text-[10px] text-slate-500 font-mono">Temp: {currentVitals.temperature}°C</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
