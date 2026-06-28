const apiBaseUrl = import.meta.env.VITE_API_BASE_URL

if (!apiBaseUrl) {
  throw new Error(
    "VITE_API_BASE_URL is not configured. Add it to frontend/.env.",
  )
}

export class ApiError extends Error {
  status: number
  payload: unknown

  constructor(
    message: string,
    status: number,
    payload: unknown,
  ) {
    super(message)

    this.name = "ApiError"
    this.status = status
    this.payload = payload
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...options.headers,
    },
  })

  const payload: unknown = await response
    .json()
    .catch(() => null)

  if (!response.ok) {
    throw new ApiError(
      `Request failed with status ${response.status}.`,
      response.status,
      payload,
    )
  }

  return payload as T
}