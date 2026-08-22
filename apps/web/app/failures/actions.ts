"use server";

export async function fetchAuditFailures() {
  const API_URL = process.env.API_URL || "http://localhost:8000";
  const response = await fetch(`${API_URL}/audit/failures?limit=50`, {
    cache: "no-store",
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch failures: ${response.statusText}`);
  }
  
  return response.json();
}
