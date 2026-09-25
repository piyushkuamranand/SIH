import React from "react";

export function ClinicalFooter() {
  return (
    <footer className="clinical-footer bg-[#020617] border-t border-slate-800/80 py-6 px-6 relative z-20">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center justify-between gap-3.5 text-xs text-white/50 text-center lg:text-left">
        <div className="clinical-footer-left">
          Facility: <strong className="text-slate-200 font-semibold">OcuScan Medical Center</strong> | Powered by Terranova AI Systems
        </div>
        <div className="clinical-footer-center text-white/40 tracking-wide text-[11px] sm:text-xs">
          HIPAA Compliant • ISO 13485 • CDSCO &amp; NABH Guidelines Applied
        </div>
        <div className="clinical-footer-right">
          Support: +91 1800-XXX-XXXX | <a href="mailto:tech@ocuscan.local" className="text-cyan-400 hover:underline">tech@ocuscan.local</a>
        </div>
      </div>
    </footer>
  );
}
