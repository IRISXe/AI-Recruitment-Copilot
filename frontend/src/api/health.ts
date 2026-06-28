import { apiRequest } from "@/api/client"

export interface HealthResponse {
  status: string
  service: string
  environment: string
}

export function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health")
}