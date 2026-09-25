"use client";

import * as React from "react";
import { LabResult } from "@/types/clinical";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FlaskConical, ArrowUpRight, ArrowDownRight, CheckCircle } from "lucide-react";

interface LabPanelsProps {
  labs: LabResult[];
}

export function LabPanelsList({ labs }: LabPanelsProps) {
  return (
    <Card className="border-slate-200 shadow-xs h-full">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <FlaskConical className="h-4 w-4 text-cyan-600" />
            <span>Stat Diagnostic Labs (Recent)</span>
          </CardTitle>
          <span className="text-[11px] text-slate-500">
            Critical chemistry, blood gas & troponin panels
          </span>
        </div>
        <Badge variant="cyan" className="text-[10px]">
          Live LIS Stream
        </Badge>
      </CardHeader>

      <CardContent className="p-4 pt-0 space-y-2">
        {labs.map((lab) => {
          const isCritical = lab.status === "critical";
          const isHigh = lab.status === "abnormal_high";
          const isLow = lab.status === "abnormal_low";

          return (
            <div
              key={lab.id}
              className={`flex items-center justify-between p-2.5 rounded-lg border text-xs transition-colors ${
                isCritical
                  ? "bg-rose-50/60 border-rose-200"
                  : isHigh || isLow
                  ? "bg-amber-50/40 border-amber-200"
                  : "bg-slate-50/50 border-slate-200"
              }`}
            >
              <div>
                <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                  <span>{lab.testName}</span>
                  <span className="text-[10px] text-slate-400 font-normal">
                    ({lab.category})
                  </span>
                </div>
                <div className="text-[10px] text-slate-500 font-mono">
                  Ref: {lab.referenceRange} {lab.unit}
                </div>
              </div>

              <div className="flex items-center gap-2 text-right">
                <div>
                  <div
                    className={`font-mono font-bold text-sm flex items-center justify-end gap-0.5 ${
                      isCritical
                        ? "text-rose-600"
                        : isHigh
                        ? "text-amber-600"
                        : isLow
                        ? "text-sky-600"
                        : "text-slate-800"
                    }`}
                  >
                    <span>{lab.value}</span>
                    <span className="text-[10px] font-normal text-slate-500 ml-0.5">
                      {lab.unit}
                    </span>
                    {isHigh && <ArrowUpRight className="h-3 w-3 text-amber-600" />}
                    {isLow && <ArrowDownRight className="h-3 w-3 text-sky-600" />}
                  </div>
                  <div className="text-[9px] text-slate-400 font-mono">{lab.timestamp}</div>
                </div>

                {isCritical ? (
                  <Badge variant="critical" className="text-[9px] px-1.5 py-0">
                    PANIC
                  </Badge>
                ) : isHigh || isLow ? (
                  <Badge variant="warning" className="text-[9px] px-1.5 py-0">
                    FLAG
                  </Badge>
                ) : (
                  <Badge variant="success" className="text-[9px] px-1.5 py-0">
                    NORMAL
                  </Badge>
                )}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
