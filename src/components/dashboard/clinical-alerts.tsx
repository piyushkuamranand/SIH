"use client";

import * as React from "react";
import { ClinicalAlert } from "@/types/clinical";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertCircle, AlertTriangle, ShieldCheck, Check, Clock } from "lucide-react";

interface ClinicalAlertsProps {
  alerts: ClinicalAlert[];
}

export function ClinicalAlertsList({ alerts }: ClinicalAlertsProps) {
  const [activeAlerts, setActiveAlerts] = React.useState<ClinicalAlert[]>(alerts);

  const handleAcknowledge = (id: string) => {
    setActiveAlerts((prev) =>
      prev.map((a) => (a.id === id ? { ...a, acknowledged: true } : a))
    );
  };

  return (
    <Card className="border-slate-200 shadow-xs flex flex-col h-full">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-rose-500" />
            <span>Clinical Early Warnings</span>
          </CardTitle>
          <span className="text-[11px] text-slate-500">
            Automated trigger & telemetry threshold alerts
          </span>
        </div>
        <Badge variant="danger" className="text-[10px]">
          {activeAlerts.filter((a) => !a.acknowledged).length} Unacknowledged
        </Badge>
      </CardHeader>

      <CardContent className="p-4 pt-0 space-y-2.5 flex-1 overflow-y-auto max-h-[380px]">
        {activeAlerts.map((alert) => {
          const isCritical = alert.severity === "critical";

          return (
            <div
              key={alert.id}
              className={`p-3 rounded-lg border transition-all ${
                alert.acknowledged
                  ? "bg-slate-50/60 border-slate-200 opacity-60"
                  : isCritical
                  ? "bg-rose-50/50 border-rose-200"
                  : "bg-amber-50/50 border-amber-200"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2">
                  {isCritical ? (
                    <AlertCircle className="h-4 w-4 text-rose-600 mt-0.5 shrink-0" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-900">
                        {alert.title}
                      </span>
                      <span className="font-mono text-[10px] px-1.5 py-0.2 bg-white rounded border text-slate-600">
                        {alert.bed}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-600 mt-0.5 font-medium">
                      {alert.patientName}: {alert.message}
                    </div>
                    <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mt-1 font-mono">
                      <Clock className="h-3 w-3" />
                      <span>{alert.timestamp}</span>
                    </div>
                  </div>
                </div>

                {!alert.acknowledged ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-6 px-2 text-[10px] border-slate-300 text-slate-700 hover:bg-white shrink-0"
                    onClick={() => handleAcknowledge(alert.id)}
                  >
                    <Check className="h-3 w-3 mr-1 text-slate-600" />
                    Ack
                  </Button>
                ) : (
                  <Badge variant="slate" className="text-[9px] px-1.5">
                    Acked
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
