"use client";

import * as React from "react";
import { Search, Bell, Filter, RefreshCw, UserCheck, Stethoscope } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function ClinicalHeader() {
  return (
    <header className="h-16 border-b border-slate-200 bg-white/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Search & Filter bar */}
      <div className="flex items-center gap-3 w-full max-w-lg">
        <Input
          placeholder="Search by Patient Name, MRN (e.g. #MRN-8492), Bed, or Doctor..."
          icon={<Search className="h-4 w-4" />}
          className="bg-slate-50 border-slate-200 focus:bg-white text-xs h-9"
        />
        <Button variant="outline" size="sm" className="shrink-0 h-9 gap-1.5 text-xs text-slate-600">
          <Filter className="h-3.5 w-3.5" />
          <span>Filters</span>
        </Button>
      </div>

      {/* Right Action Icons & Clinical User Profile */}
      <div className="flex items-center gap-4">
        {/* Live status badge */}
        <div className="hidden sm:flex items-center gap-2 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-[11px] font-semibold text-emerald-800">Telemetry Live (0.4s)</span>
        </div>

        {/* Sync button */}
        <Button variant="ghost" size="icon" className="h-9 w-9 text-slate-500 hover:text-slate-800">
          <RefreshCw className="h-4 w-4" />
        </Button>

        {/* Notification Alert Bell */}
        <div className="relative">
          <Button variant="ghost" size="icon" className="h-9 w-9 text-slate-600 hover:text-slate-900">
            <Bell className="h-4 w-4" />
          </Button>
          <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
          </span>
        </div>

        <div className="h-6 w-[1px] bg-slate-200"></div>

        {/* Active Clinician Profile */}
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-full bg-cyan-100 border border-cyan-300 flex items-center justify-center text-cyan-800 font-bold text-xs shadow-xs">
            DR
          </div>
          <div className="hidden md:block text-left">
            <div className="text-xs font-semibold text-slate-900 leading-tight">
              Dr. Sarah Chen, MD
            </div>
            <div className="text-[11px] text-slate-500 font-medium">
              Attending Intensivist • Ward 4-East
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
