"use client";

import React from "react";
import { SvgGlassFilters } from "@/components/ui/svg-filters";
import { RetinalBackgroundCanvas } from "@/components/canvas/retinal-canvas";
import { PortalNav } from "@/components/layout/portal-nav";
import { LeftColumnLede } from "@/components/hero/left-column-lede";
import { LiquidGlassCard } from "@/components/glass/liquid-glass-card";
import { RolesSection } from "@/components/home/roles-section";
import { DrEducationSection } from "@/components/home/dr-education";
import { ClinicalFooter } from "@/components/layout/clinical-footer";

export default function OcuScanSuitePage() {
  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-x-hidden">
      {/* SVG Displacement / Refraction Filters (Scales 65/56/47) */}
      <SvgGlassFilters />

      {/* Video & Real-time Canvas Rendering Layer (Fixed Background) */}
      <RetinalBackgroundCanvas />

      {/* Top Portal Header & Navigation */}
      <PortalNav />

      {/* 1. Hero Section (100vh / min-h-[calc(100vh-80px)]) */}
      <main className="hero relative z-10 min-h-[calc(100vh-80px)] flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Column (Lede) */}
          <div className="lg:col-span-7 flex flex-col justify-center">
            <LeftColumnLede />
          </div>

          {/* Right Column (Liquid Glass Card) */}
          <div className="lg:col-span-5 flex justify-center lg:justify-end">
            <LiquidGlassCard />
          </div>
        </div>
      </main>

      {/* 2. Prominent Role Selection Section immediately below hero */}
      <RolesSection />

      {/* 3. Disease Progression Educational Section */}
      <DrEducationSection />

      {/* 4. Compact Clinical Regulatory Footer */}
      <ClinicalFooter />
    </div>
  );
}
