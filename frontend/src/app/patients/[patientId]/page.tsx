import { PatientDetailScreen } from "@/components/patient-detail";

export default async function PatientPage({ params }: { params: Promise<{ patientId: string }> }) {
  const { patientId } = await params;
  return <PatientDetailScreen patientId={patientId} />;
}
