/**
 * ui.js
 * OcuScan AI - UI interactions & Slide-in Menu
 */

(function () {
  "use strict";

  const menuTrigger = document.getElementById("menu-trigger");
  const menuClose = document.getElementById("menu-close");
  const menuOverlay = document.getElementById("menu-overlay");

  function openMenu() {
    if (menuOverlay) menuOverlay.classList.add("open");
  }

  function closeMenu() {
    if (menuOverlay) menuOverlay.classList.remove("open");
  }

  if (menuTrigger) {
    menuTrigger.addEventListener("click", openMenu);
  }

  if (menuClose) {
    menuClose.addEventListener("click", closeMenu);
  }

  if (menuOverlay) {
    menuOverlay.addEventListener("click", function (e) {
      if (e.target === menuOverlay) {
        closeMenu();
      }
    });
  }

  // Smooth scroll for internal anchors
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener("click", function (e) {
      const targetId = this.getAttribute("href");
      if (targetId && targetId !== "#") {
        const targetEl = document.querySelector(targetId);
        if (targetEl) {
          e.preventDefault();
          closeMenu();
          targetEl.scrollIntoView({ behavior: "smooth" });
        }
      }
    });
  });

  // Background Canvas Animation (Retinal vascular & neural particles)
  const canvas = document.getElementById("bg-canvas");
  if (canvas) {
    const ctx = canvas.getContext("2d");
    if (ctx) {
      let w = (canvas.width = window.innerWidth);
      let h = (canvas.height = window.innerHeight);

      window.addEventListener("resize", function () {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
      });

      const particles = Array.from({ length: 40 }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        radius: Math.random() * 2 + 1,
        color: Math.random() > 0.5 ? "#22d3ee" : "#38bdf8",
        alpha: Math.random() * 0.5 + 0.2,
      }));

      let t = 0;
      function animate() {
        t += 0.008;
        ctx.fillStyle = "rgba(11, 17, 32, 0.25)";
        ctx.fillRect(0, 0, w, h);

        // Optical center gradient
        const cx = w * 0.65;
        const cy = h * 0.5;
        const grad = ctx.createRadialGradient(cx, cy, 50, cx, cy, Math.max(w, h) * 0.6);
        grad.addColorStop(0, "rgba(8, 145, 178, 0.15)");
        grad.addColorStop(0.5, "rgba(2, 132, 199, 0.05)");
        grad.addColorStop(1, "rgba(11, 17, 32, 0)");
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, w, h);

        // Vascular arcs
        ctx.beginPath();
        ctx.strokeStyle = "rgba(34, 211, 238, 0.12)";
        ctx.lineWidth = 1.5;
        for (let i = 0; i < 5; i++) {
          const angle = (i * Math.PI) / 2.5 + t * 0.1;
          const x1 = cx + Math.cos(angle) * 70;
          const y1 = cy + Math.sin(angle) * 70;
          const x2 = cx + Math.cos(angle + 0.3) * (220 + Math.sin(t + i) * 30);
          const y2 = cy + Math.sin(angle + 0.3) * (220 + Math.cos(t + i) * 30);
          ctx.moveTo(x1, y1);
          ctx.quadraticCurveTo(cx + Math.cos(angle + 0.1) * 150, cy + Math.sin(angle + 0.1) * 150, x2, y2);
        }
        ctx.stroke();

        // Particles
        particles.forEach(function (p) {
          p.x += p.vx;
          p.y += p.vy;
          if (p.x < 0) p.x = w;
          if (p.x > w) p.x = 0;
          if (p.y < 0) p.y = h;
          if (p.y > h) p.y = 0;

          ctx.beginPath();
          ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
          ctx.fillStyle = p.color;
          ctx.globalAlpha = p.alpha;
          ctx.fill();
          ctx.globalAlpha = 1;
        });

        requestAnimationFrame(animate);
      }
      animate();
    }
  }

  // Liquid Glass Card Tilt Effect (frame-sync)
  const glassCard = document.querySelector(".liquid-glass-card");
  if (glassCard) {
    let targetX = 0, targetY = 0, currX = 0, currY = 0;

    window.addEventListener("mousemove", function (e) {
      const rect = glassCard.getBoundingClientRect();
      const x = e.clientX - (rect.left + rect.width / 2);
      const y = e.clientY - (rect.top + rect.height / 2);
      targetX = (-y / rect.height) * 8;
      targetY = (x / rect.width) * 8;
    });

    glassCard.addEventListener("mouseleave", function () {
      targetX = 0;
      targetY = 0;
    });

    function tiltLoop() {
      currX += (targetX - currX) * 0.08;
      currY += (targetY - currY) * 0.08;
      glassCard.style.transform = `perspective(1000px) rotateX(${currX}deg) rotateY(${currY}deg)`;
      requestAnimationFrame(tiltLoop);
    }
    tiltLoop();
  }
})();
