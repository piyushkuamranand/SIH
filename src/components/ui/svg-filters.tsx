import React from "react";

export function SvgGlassFilters() {
  return (
    <svg className="pointer-events-none absolute h-0 w-0" aria-hidden="true">
      <defs>
        {/* Exact Chromatic Aberration & Refraction Scales: 65 (Red), 56 (Green), 47 (Blue) */}
        <filter id="glass-distortion" x="-20%" y="-20%" width="140%" height="140%">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.015 0.015"
            numOctaves="3"
            result="noise"
            seed="42"
          />
          <feDisplacementMap
            in="SourceGraphic"
            in2="noise"
            scale="65"
            xChannelSelector="R"
            yChannelSelector="G"
            result="displacedRed"
          />
          <feDisplacementMap
            in="SourceGraphic"
            in2="noise"
            scale="56"
            xChannelSelector="G"
            yChannelSelector="B"
            result="displacedGreen"
          />
          <feDisplacementMap
            in="SourceGraphic"
            in2="noise"
            scale="47"
            xChannelSelector="B"
            yChannelSelector="R"
            result="displacedBlue"
          />
          <feBlend in="displacedRed" in2="displacedGreen" mode="screen" result="blendRG" />
          <feBlend in="blendRG" in2="displacedBlue" mode="screen" />
        </filter>

        <filter id="liquid-refraction" x="-10%" y="-10%" width="120%" height="120%">
          <feTurbulence
            type="turbulence"
            baseFrequency="0.02 0.02"
            numOctaves="2"
            result="turb"
          />
          <feDisplacementMap
            in2="turb"
            in="SourceGraphic"
            scale="47"
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
      </defs>
    </svg>
  );
}
