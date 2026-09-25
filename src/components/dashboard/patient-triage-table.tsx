"use client";

import * as React from "react";
import { Patient } from "@/types/clinical";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { 
  Heart, 
  Activity, 
  Wind, 
  Thermometer, 
  MoreHorizontal, 
  Eye, 
  FileEdit, 
  CheckCircle2,
  AlertTriangle 
} from "lucide-react";

interface PatientTriageTableProps {
  patients: Patient[];
  onSelectPatient?: (patient: Patient) => void;
}

export function PatientTriageTable({ patients, onSelectPatient }: PatientTriageTableProps) {
  const getAcuityBadge = (acuity: number) => {
    switch (acuity) {
      case 1:
        return <Badge variant="critical" className="font-mono">Level 1 • Critical</Badge>;
      case 2:
        return <Badge variant="danger" dot dotColor="rose">Level 2 • Emergent</Badge>;
      case 3:
        return <Badge variant="warning" dot dotColor="amber">Level 3 • Urgent</Badge>;
      case 4:
        return <Badge variant="cyan" dot dotColor="cyan">Level 4 • Semi-Urgent</Badge>;
      default:
        return <Badge variant="slate" dot dotColor="slate">Level 5 • Stable</Badge>;
    }
  };

  return (
    <Card className="w-full border-slate-200 shadow-xs">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div>
          <CardTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
            <span>Inpatient & Triage Roster</span>
            <Badge variant="blue" className="text-[11px] font-normal">
              {patients.length} Monitored
            </Badge>
          </CardTitle>
          <CardDescription>
            Live continuous monitoring for ICU Ward 4-East & Resuscitation Bays
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="text-xs h-8">
            Export Roster
          </Button>
          <Button variant="primary" size="sm" className="text-xs h-8 bg-sky-600 hover:bg-sky-700">
            + Admit Patient
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-y border-slate-200 bg-slate-50/80 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4">Patient & MRN</th>
                <th className="py-3 px-3">Location</th>
                <th className="py-3 px-3">Acuity</th>
                <th className="py-3 px-3">HR (bpm)</th>
                <th className="py-3 px-3">BP (mmHg)</th>
                <th className="py-3 px-3">SpO₂</th>
                <th className="py-3 px-3">Temp</th>
                <th className="py-3 px-3">Primary Diagnosis</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {patients.map((patient) => {
                const isCriticalHR =
                  patient.currentVitals.heartRate > 115 ||
                  patient.currentVitals.heartRate < 55;
                const isCriticalSpO2 = patient.currentVitals.oxygenSaturation < 93;
                const isElevatedBP = patient.currentVitals.bloodPressureSystolic > 140;

                return (
                  <tr
                    key={patient.id}
                    className="hover:bg-slate-50/70 transition-colors group cursor-pointer"
                    onClick={() => onSelectPatient?.(patient)}
                  >
                    {/* Patient & MRN */}
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900 group-hover:text-cyan-700 transition-colors flex items-center gap-2">
                        <span>{patient.fullName}</span>
                        <span className="text-[11px] font-normal text-slate-400">
                          ({patient.age}y, {patient.gender[0]})
                        </span>
                      </div>
                      <div className="text-[11px] font-mono text-slate-400">
                        {patient.mrn} • Dr. {patient.attendingPhysician.split(" ").slice(-1)[0]}
                      </div>
                    </td>

                    {/* Bed */}
                    <td className="py-3 px-3">
                      <span className="font-mono font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 text-[11px]">
                        {patient.bedNumber}
                      </span>
                    </td>

                    {/* Acuity */}
                    <td className="py-3 px-3">
                      {getAcuityBadge(patient.acuity)}
                    </td>

                    {/* HR */}
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-1.5 font-mono">
                        <Heart
                          className={`h-3.5 w-3.5 ${
                            isCriticalHR ? "text-rose-500 fill-rose-500 animate-pulse" : "text-slate-400"
                          }`}
                        />
                        <span className={`font-semibold ${isCriticalHR ? "text-rose-600 font-bold" : "text-slate-800"}`}>
                          {patient.currentVitals.heartRate}
                        </span>
                      </div>
                    </td>

                    {/* BP */}
                    <td className="py-3 px-3">
                      <span
                        className={`font-mono font-medium ${
                          isElevatedBP ? "text-amber-700 font-semibold" : "text-slate-800"
                        }`}
                      >
                        {patient.currentVitals.bloodPressureSystolic}/
                        {patient.currentVitals.bloodPressureDiastolic}
                      </span>
                    </td>

                    {/* SpO2 */}
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-1 font-mono">
                        <Wind
                          className={`h-3.5 w-3.5 ${
                            isCriticalSpO2 ? "text-rose-500" : "text-cyan-500"
                          }`}
                        />
                        <span
                          className={`font-semibold ${
                            isCriticalSpO2 ? "text-rose-600 font-bold" : "text-slate-800"
                          }`}
                        >
                          {patient.currentVitals.oxygenSaturation}%
                        </span>
                      </div>
                    </td>

                    {/* Temp */}
                    <td className="py-3 px-3">
                      <span className="font-mono text-slate-700">
                        {patient.currentVitals.temperature}°C
                      </span>
                    </td>

                    {/* Chief Complaint */}
                    <td className="py-3 px-3 max-w-[180px] truncate text-slate-600 font-medium">
                      {patient.chiefComplaint}
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-slate-400 hover:text-cyan-700"
                          title="View Chart"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-slate-400 hover:text-slate-700"
                          title="Record Vitals"
                        >
                          <FileEdit className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
