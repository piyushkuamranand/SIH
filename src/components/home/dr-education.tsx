import React from "react";

export function DrEducationSection() {
  return (
    <section className="dr-education bg-slate-50 text-slate-900 py-24 px-6 relative z-10 border-t border-slate-200">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center max-w-2xl mx-auto mb-14">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-sky-100 border border-sky-200 text-sky-700 text-xs font-mono font-bold uppercase tracking-wider mb-3">
            <span>●</span>
            <span>ETDRS Severity Classification</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-slate-900 mb-3">
            Diabetic Retinopathy (DR) Progression Mapping
          </h2>
          <p className="text-slate-600 text-sm sm:text-base leading-relaxed">
            Comparative fundus pathology across key stages of diabetic eye disease, from healthy microvascular integrity to sight-threatening proliferative neovascularization.
          </p>
        </div>

        {/* 3-Column Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          
          {/* Card 1: Normal */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 overflow-hidden flex flex-col">
            <div className="bg-[#090d16] p-7 flex items-center justify-center border-b border-slate-100">
              <svg className="w-44 h-44 rounded-full shadow-2xl" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <radialGradient id="nBg" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#732204"/>
                    <stop offset="60%" stopColor="#4a1200"/>
                    <stop offset="100%" stopColor="#1e0500"/>
                  </radialGradient>
                  <radialGradient id="nDisc" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#fff8db"/>
                    <stop offset="50%" stopColor="#fde047"/>
                    <stop offset="100%" stopColor="#d97706"/>
                  </radialGradient>
                  <clipPath id="nClip">
                    <circle cx="100" cy="100" r="96"/>
                  </clipPath>
                </defs>
                <circle cx="100" cy="100" r="98" fill="#1e0500"/>
                <g clipPath="url(#nClip)">
                  <circle cx="100" cy="100" r="96" fill="url(#nBg)"/>
                  <circle cx="65" cy="98" r="16" fill="url(#nDisc)"/>
                  <circle cx="65" cy="98" r="9" fill="#fffbeb" opacity="0.8"/>
                  <circle cx="118" cy="102" r="18" fill="#290700" opacity="0.7"/>
                  <circle cx="118" cy="102" r="3" fill="#ff7043" opacity="0.4"/>
                  <path d="M65,92 Q78,72 100,68 Q125,65 145,60 Q162,56 178,65" fill="none" stroke="#dc2626" strokeWidth="2.2" strokeLinecap="round"/>
                  <path d="M65,92 Q78,72 100,68 Q125,65 145,60 Q162,56 178,65" fill="none" stroke="#f87171" strokeWidth="0.9" strokeLinecap="round"/>
                  <path d="M65,104 Q80,122 102,128 Q126,132 148,130 Q165,126 182,118" fill="none" stroke="#dc2626" strokeWidth="2.2" strokeLinecap="round"/>
                  <path d="M65,104 Q80,122 102,128 Q126,132 148,130 Q165,126 182,118" fill="none" stroke="#f87171" strokeWidth="0.9" strokeLinecap="round"/>
                  <path d="M65,95 Q82,82 104,78 Q128,75 148,72" fill="none" stroke="#991b1b" strokeWidth="2.6" strokeLinecap="round"/>
                  <path d="M65,101 Q82,115 104,122 Q128,124 150,120" fill="none" stroke="#991b1b" strokeWidth="2.6" strokeLinecap="round"/>
                  <path d="M100,68 Q108,82 106,94" fill="none" stroke="#b91c1c" strokeWidth="1.2"/>
                  <path d="M125,65 Q130,80 128,92" fill="none" stroke="#b91c1c" strokeWidth="1"/>
                  <path d="M102,128 Q108,114 107,104" fill="none" stroke="#b91c1c" strokeWidth="1.2"/>
                  <circle cx="100" cy="100" r="96" fill="none" stroke="#000" strokeWidth="10" opacity="0.6"/>
                </g>
              </svg>
            </div>
            <div className="p-7 flex flex-col flex-1">
              <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-mono font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-200 mb-3 w-fit">
                Stage 0 · Normal
              </span>
              <h3 className="text-xl font-bold text-slate-900 mb-2">Healthy / Normal Retina</h3>
              <p className="text-slate-600 text-sm leading-relaxed flex-1">
                Clear macula and optic disc. No visible lesions, hemorrhages, or microaneurysms.
              </p>
              <div className="mt-5 pt-4 border-t border-slate-100 flex flex-wrap gap-1.5">
                <span className="text-xs font-mono px-2 py-0.5 bg-slate-100 text-slate-600 rounded">Vessels Intact</span>
                <span className="text-xs font-mono px-2 py-0.5 bg-slate-100 text-slate-600 rounded">Zero Lesions</span>
                <span className="text-xs font-mono px-2 py-0.5 bg-slate-100 text-slate-600 rounded">Normal Foveal Reflex</span>
              </div>
            </div>
          </div>

          {/* Card 2: Moderate NPDR */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 overflow-hidden flex flex-col">
            <div className="bg-[#090d16] p-7 flex items-center justify-center border-b border-slate-100">
              <svg className="w-44 h-44 rounded-full shadow-2xl" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <radialGradient id="mBg" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#6e2003"/>
                    <stop offset="60%" stopColor="#451100"/>
                    <stop offset="100%" stopColor="#1a0400"/>
                  </radialGradient>
                  <radialGradient id="mDisc" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#fff8db"/>
                    <stop offset="50%" stopColor="#fde047"/>
                    <stop offset="100%" stopColor="#d97706"/>
                  </radialGradient>
                  <clipPath id="mClip">
                    <circle cx="100" cy="100" r="96"/>
                  </clipPath>
                </defs>
                <circle cx="100" cy="100" r="98" fill="#1a0400"/>
                <g clipPath="url(#mClip)">
                  <circle cx="100" cy="100" r="96" fill="url(#mBg)"/>
                  <circle cx="65" cy="98" r="16" fill="url(#mDisc)"/>
                  <circle cx="65" cy="98" r="9" fill="#fffbeb" opacity="0.8"/>
                  <circle cx="118" cy="102" r="18" fill="#240600" opacity="0.75"/>
                  <path d="M65,92 Q78,72 100,68 Q125,65 145,60 Q162,56 178,65" fill="none" stroke="#dc2626" strokeWidth="2.2" strokeLinecap="round"/>
                  <path d="M65,104 Q80,122 102,128 Q126,132 148,130 Q165,126 182,118" fill="none" stroke="#dc2626" strokeWidth="2.2" strokeLinecap="round"/>
                  <path d="M65,95 Q82,82 104,78 Q128,75 148,72" fill="none" stroke="#991b1b" strokeWidth="2.6" strokeLinecap="round"/>
                  <path d="M65,101 Q82,115 104,122 Q128,124 150,120" fill="none" stroke="#991b1b" strokeWidth="2.6" strokeLinecap="round"/>
                  {/* Hemorrhages */}
                  <circle cx="110" cy="85" r="3.2" fill="#7f1d1d"/>
                  <ellipse cx="132" cy="78" rx="4" ry="2.6" fill="#7f1d1d" transform="rotate(-15,132,78)"/>
                  <circle cx="94" cy="115" r="2.8" fill="#7f1d1d"/>
                  <ellipse cx="128" cy="122" rx="4.5" ry="3" fill="#881337" transform="rotate(20,128,122)"/>
                  <circle cx="146" cy="112" r="3" fill="#7f1d1d"/>
                  {/* Microaneurysms */}
                  <circle cx="106" cy="74" r="1.4" fill="#ef4444"/>
                  <circle cx="118" cy="80" r="1.3" fill="#ef4444"/>
                  <circle cx="124" cy="88" r="1.5" fill="#ef4444"/>
                  <circle cx="138" cy="94" r="1.3" fill="#ef4444"/>
                  <circle cx="112" cy="118" r="1.4" fill="#ef4444"/>
                  <circle cx="138" cy="128" r="1.3" fill="#ef4444"/>
                  {/* Hard Exudates */}
                  <ellipse cx="140" cy="82" rx="3.5" ry="2" fill="#fef08a" opacity="0.85" transform="rotate(25,140,82)"/>
                  <circle cx="144" cy="86" r="2" fill="#fef9c3" opacity="0.9"/>
                  <circle cx="136" cy="86" r="1.8" fill="#fef08a" opacity="0.85"/>
                  <ellipse cx="148" cy="90" rx="2.8" ry="1.7" fill="#fde047" opacity="0.8" transform="rotate(-10,148,90)"/>
                  <circle cx="100" cy="100" r="96" fill="none" stroke="#000" strokeWidth="10" opacity="0.6"/>
                </g>
              </svg>
            </div>
            <div className="p-7 flex flex-col flex-1">
              <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-mono font-bold uppercase tracking-wider bg-amber-100 text-amber-800 border border-amber-200 mb-3 w-fit">
                Stage 2 · Moderate
              </span>
              <h3 className="text-xl font-bold text-slate-900 mb-2">Moderate NPDR</h3>
              <p className="text-slate-600 text-sm leading-relaxed flex-1">
                Presence of dot-and-blot hemorrhages, hard exudates, and early microaneurysms.
              </p>
              <div className="mt-5 pt-4 border-t border-slate-100 flex flex-wrap gap-1.5">
                <span className="text-xs font-mono px-2 py-0.5 bg-slate-100 text-slate-600 rounded">Microaneurysms (MA)</span>
                <span className="text-xs font-mono px-2 py-0.5 bg-slate-100 text-slate-600 rounded">Blot Hemorrhages</span>
                <span className="text-xs font-mono px-2 py-0.5 bg-slate-100 text-slate-600 rounded">Hard Exudates (EX)</span>
              </div>
            </div>
          </div>

          {/* Card 3: Proliferative DR */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 overflow-hidden flex flex-col">
            <div className="bg-[#090d16] p-7 flex items-center justify-center border-b border-slate-100">
              <svg className="w-44 h-44 rounded-full shadow-2xl" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <radialGradient id="pBg" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#611902"/>
                    <stop offset="60%" stopColor="#3c0c00"/>
                    <stop offset="100%" stopColor="#140300"/>
                  </radialGradient>
                  <radialGradient id="pDisc" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#fff8db"/>
                    <stop offset="50%" stopColor="#fde047"/>
                    <stop offset="100%" stopColor="#d97706"/>
                  </radialGradient>
                  <clipPath id="pClip">
                    <circle cx="100" cy="100" r="96"/>
                  </clipPath>
                </defs>
                <circle cx="100" cy="100" r="98" fill="#140300"/>
                <g clipPath="url(#pClip)">
                  <circle cx="100" cy="100" r="96" fill="url(#pBg)"/>
                  <circle cx="65" cy="98" r="16" fill="url(#pDisc)"/>
                  <circle cx="118" cy="102" r="18" fill="#1f0400" opacity="0.8"/>
                  <path d="M65,92 Q74,68 96,66 Q118,64 140,56 Q158,50 176,60" fill="none" stroke="#b91c1c" strokeWidth="2.8" strokeLinecap="round"/>
                  <path d="M65,104 Q76,126 98,132 Q122,136 145,133 Q164,130 182,118" fill="none" stroke="#b91c1c" strokeWidth="2.8" strokeLinecap="round"/>
                  {/* Neovascularization fronds */}
                  <path d="M62,94 Q56,84 66,78 Q74,74 70,86 Q76,82 82,88 Q78,96 86,94" fill="none" stroke="#ef4444" strokeWidth="1.3" strokeLinecap="round"/>
                  <path d="M65,102 Q60,114 70,118 Q78,122 75,108 Q82,112 88,106" fill="none" stroke="#ef4444" strokeWidth="1.3" strokeLinecap="round"/>
                  <path d="M125,65 Q130,55 138,58 Q144,52 142,64 Q148,60 152,66" fill="none" stroke="#ef4444" strokeWidth="1.2"/>
                  {/* Preretinal hemorrhage */}
                  <path d="M105,96 Q122,94 138,98 Q140,112 125,116 Q108,116 105,96 Z" fill="#7f1d1d" opacity="0.9"/>
                  <ellipse cx="86" cy="120" rx="9" ry="5" fill="#581c87" opacity="0.4" transform="rotate(-15,86,120)"/>
                  <ellipse cx="86" cy="120" rx="7" ry="4" fill="#7f1d1d" opacity="0.8" transform="rotate(-15,86,120)"/>
                  <circle cx="158" cy="110" r="4.5" fill="#881337"/>
                  <circle cx="100" cy="100" r="96" fill="none" stroke="#000" strokeWidth="10" opacity="0.6"/>
                </g>
              </svg>
            </div>
            <div className="p-7 flex flex-col flex-1">
              <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-mono font-bold uppercase tracking-wider bg-rose-100 text-rose-800 border border-rose-200 mb-3 w-fit">
                Stage 4 · Proliferative
              </span>
              <h3 className="text-xl font-bold text-slate-900 mb-2">Proliferative DR (PDR)</h3>
              <p className="text-slate-600 text-sm leading-relaxed flex-1">
                Advanced stage. Neovascularization (fragile new blood vessels) and high risk of vitreous hemorrhage or detachment.
              </p>
              <div className="mt-5 pt-4 border-t border-slate-100 flex flex-wrap gap-1.5">
                <span className="text-xs font-mono px-2 py-0.5 bg-slate-100 text-slate-600 rounded">Neovascularization (NV)</span>
                <span className="text-xs font-mono px-2 py-0.5 bg-slate-100 text-slate-600 rounded">Preretinal Bleeds</span>
                <span className="text-xs font-mono px-2 py-0.5 bg-slate-100 text-slate-600 rounded">High Detachment Risk</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
