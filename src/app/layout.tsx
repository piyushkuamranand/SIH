import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OcuScan AI | Clinical Retinal Suite",
  description: "Enterprise diagnostic pipeline for Diabetic Retinopathy. Integrating real-time computer vision with ophthalmology workflows.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased bg-[#0b1120] text-slate-100">
      <body className="min-h-full flex flex-col relative overflow-x-hidden overflow-y-auto font-sans selection:bg-cyan-500 selection:text-slate-950">
        {children}
      </body>
    </html>
  );
}
