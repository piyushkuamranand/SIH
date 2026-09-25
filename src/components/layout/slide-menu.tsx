"use client";

import React, { useState } from "react";
import { 
  Menu, 
  X, 
  HelpCircle, 
  BookOpen, 
  Activity, 
  LifeBuoy, 
  Mail, 
  ShieldCheck, 
  ChevronRight 
} from "lucide-react";

export function SlideMenu() {
  const [isOpen, setIsOpen] = useState(false);

  const menuLinks = [
    { label: "FAQ", icon: HelpCircle, href: "#faq", tag: "General" },
    { label: "Documentation", icon: BookOpen, href: "#docs", tag: "API & SDK" },
    { label: "API Status", icon: Activity, href: "#status", tag: "99.99% Uptime" },
    { label: "Help & Support", icon: LifeBuoy, href: "#support", tag: "24/7 Triage" },
  ];

  return (
    <>
      {/* Menu Hamburger Trigger */}
      <button
        onClick={() => setIsOpen(true)}
        className="p-2.5 rounded-xl bg-slate-900/70 border border-slate-700/80 text-cyan-300 hover:text-white hover:bg-slate-800 transition-all shadow-md backdrop-blur-md cursor-pointer"
        aria-label="Open navigation menu"
      >
        <Menu className="h-5 w-5 stroke-[2.2]" />
      </button>

      {/* Backdrop overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-40 transition-opacity duration-300"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Slide-in Panel */}
      <div
        className={`fixed top-0 right-0 h-full w-full max-w-sm bg-slate-900/95 border-l border-slate-700/80 backdrop-blur-2xl z-50 p-6 flex flex-col justify-between shadow-2xl transform transition-transform duration-300 ease-out text-white ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-5 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-md bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center text-cyan-300">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <span className="font-mono text-xs font-bold text-slate-200 uppercase tracking-wider">
                System Resources
              </span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Nav Links */}
          <nav className="mt-6 space-y-2.5">
            {menuLinks.map((link) => {
              const Icon = link.icon;
              return (
                <a
                  key={link.label}
                  href={link.href}
                  onClick={() => setIsOpen(false)}
                  className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-cyan-500/50 hover:bg-slate-800/60 transition-all group cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-slate-900 text-cyan-400 group-hover:text-cyan-300 transition-colors">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-slate-100 group-hover:text-cyan-300 transition-colors">
                        {link.label}
                      </div>
                      <div className="text-[10px] font-mono text-slate-400">
                        {link.tag}
                      </div>
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-slate-500 group-hover:text-cyan-400 transition-colors" />
                </a>
              );
            })}
          </nav>
        </div>

        {/* Footer Contact */}
        <div className="pt-6 border-t border-slate-800 space-y-3">
          <div className="text-xs text-slate-400">Clinical Support & Triage</div>
          <a
            href="mailto:support@ocuscan.hospital.local"
            className="flex items-center gap-2 text-xs font-mono text-cyan-300 hover:text-cyan-200 transition-colors"
          >
            <Mail className="h-4 w-4 text-cyan-400 shrink-0" />
            <span>support@ocuscan.hospital.local</span>
          </a>
          <div className="text-[10px] text-slate-500 font-mono">
            OcuScan AI v2.4 • Hospital Local Node
          </div>
        </div>
      </div>
    </>
  );
}
