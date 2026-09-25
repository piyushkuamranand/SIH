"use client";

import React, { useEffect, useRef } from "react";

export function RetinalBackgroundCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener("resize", handleResize);

    // Particles simulating retinal vascular stream & neural optical field
    const particles = Array.from({ length: 45 }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      radius: Math.random() * 2 + 1,
      color: Math.random() > 0.6 ? "#22d3ee" : "#38bdf8",
      alpha: Math.random() * 0.5 + 0.2,
    }));

    let time = 0;

    const render = () => {
      time += 0.008;
      ctx.fillStyle = "rgba(11, 17, 32, 0.25)";
      ctx.fillRect(0, 0, width, height);

      // Draw subtle glowing optical rings
      const centerX = width * 0.65;
      const centerY = height * 0.5;

      const gradient = ctx.createRadialGradient(
        centerX,
        centerY,
        50,
        centerX,
        centerY,
        Math.max(width, height) * 0.6
      );
      gradient.addColorStop(0, "rgba(8, 145, 178, 0.15)");
      gradient.addColorStop(0.4, "rgba(2, 132, 199, 0.08)");
      gradient.addColorStop(1, "rgba(11, 17, 32, 0)");

      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      // Draw vascular neural filaments
      ctx.beginPath();
      ctx.strokeStyle = "rgba(34, 211, 238, 0.12)";
      ctx.lineWidth = 1.5;
      for (let i = 0; i < 6; i++) {
        const angle = (i * Math.PI) / 3 + time * 0.1;
        const x1 = centerX + Math.cos(angle) * 80;
        const y1 = centerY + Math.sin(angle) * 80;
        const x2 = centerX + Math.cos(angle + 0.3) * (240 + Math.sin(time + i) * 30);
        const y2 = centerY + Math.sin(angle + 0.3) * (240 + Math.cos(time + i) * 30);
        ctx.moveTo(x1, y1);
        ctx.quadraticCurveTo(
          centerX + Math.cos(angle + 0.1) * 160,
          centerY + Math.sin(angle + 0.1) * 160,
          x2,
          y2
        );
      }
      ctx.stroke();

      // Update & draw particles
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.alpha;
        ctx.fill();
        ctx.globalAlpha = 1;
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas
      id="bg-canvas"
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0 h-full w-full bg-[#0b1120]"
    />
  );
}
