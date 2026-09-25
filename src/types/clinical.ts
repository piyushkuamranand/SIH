export type AcuityLevel = 1 | 2 | 3 | 4 | 5;

export type PatientStatus = "admitted" | "triage" | "under_observation" | "in_surgery" | "discharged";

export interface VitalSignReading {
  id: string;
  patientId: string;
  timestamp: string;
  heartRate: number; // bpm
  bloodPressureSystolic: number; // mmHg
  bloodPressureDiastolic: number; // mmHg
  oxygenSaturation: number; // %
  respiratoryRate: number; // bpm
  temperature: number; // °C
  painScore?: number; // 0-10
}

export interface Patient {
  id: string;
  mrn: string; // Medical Record Number
  fullName: string;
  age: number;
  gender: "Male" | "Female" | "Other";
  bedNumber: string;
  ward: string;
  attendingPhysician: string;
  admissionDate: string;
  chiefComplaint: string;
  status: PatientStatus;
  acuity: AcuityLevel;
  allergies: string[];
  currentVitals: VitalSignReading;
}

export interface LabResult {
  id: string;
  testName: string;
  category: "Hematology" | "Biochemistry" | "Blood Gas" | "Electrolytes";
  value: string | number;
  unit: string;
  referenceRange: string;
  status: "normal" | "abnormal_low" | "abnormal_high" | "critical";
  timestamp: string;
}

export interface ClinicalAlert {
  id: string;
  patientId: string;
  patientName: string;
  bed: string;
  type: "critical_vital" | "lab_panic" | "drug_interaction" | "fall_risk";
  title: string;
  message: string;
  timestamp: string;
  acknowledged: boolean;
  severity: "info" | "warning" | "critical";
}

export interface MedicationOrder {
  id: string;
  medicationName: string;
  dosage: string;
  route: "IV" | "Oral" | "Subcutaneous" | "Inhalation" | "Topical";
  frequency: string;
  status: "active" | "held" | "completed" | "discontinued";
  prescribedBy: string;
  nextDose: string;
}
