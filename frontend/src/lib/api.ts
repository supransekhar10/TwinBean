export type DoctorHealth = {
  service: string;
  status: string;
  authorization: "doctor";
  uid: string;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchDoctorHealth(idToken: string): Promise<DoctorHealth> {
  const response = await fetch(`${apiBaseUrl}/health/authenticated`, {
    headers: { Authorization: `Bearer ${idToken}` },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Health check failed (${response.status}).`);
  }

  return response.json() as Promise<DoctorHealth>;
}
