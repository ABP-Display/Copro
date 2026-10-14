export type Organization = { id: number; name: string };
export type User = {
  username: string;
  is_manager: boolean;
  is_admin?: boolean;
  is_former_owner?: boolean;
  must_change_password?: boolean;
  display_name?: string;
};
export type Owner = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  lots_count: number;
  has_access?: boolean;
  must_change_password?: boolean;
};
export type Lot = {
  id: number;
  number: string;
  kind: string;
  floor: string;
  area: string;
  shares: string;
  owner: number | null;
  owner_name: string;
};
export type Overview = {
  owners_count: number;
  lots_count: number;
  unassigned_count: number;
  shares_total: string;
  kinds: { kind: string; count: number }[];
};

let token = "";
export function newOperationId() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  const h = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const [pathname, query] = path.split("?", 2);
  const multipart = body instanceof FormData;
  const response = await fetch(`/api/${pathname}/${query ? `?${query}` : ""}`, {
    method,
    credentials: "same-origin",
    headers: {
      ...(!multipart ? { "Content-Type": "application/json" } : {}),
      ...(method !== "GET" ? { "X-CSRFToken": token } : {}),
    },
    body:
      body === undefined
        ? undefined
        : multipart
          ? (body as FormData)
          : JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({
    error: "Le serveur est indisponible. Réessayez dans un instant.",
  }));
  if (data.csrfToken) token = data.csrfToken;
  if (!response.ok) {
    const fields = data.fields
      ? Object.entries(data.fields)
          .map(
            ([key, errors]) =>
              `${fieldLabels[key] || key} : ${(errors as string[]).join(" ")}`,
          )
          .join(" · ")
      : "";
    throw new ApiError(
      fields || data.error || "Une erreur est survenue.",
      response.status,
    );
  }
  return data as T;
}
const fieldLabels: Record<string, string> = {
  first_name: "Prénom",
  last_name: "Nom",
  email: "Courriel",
  phone: "Téléphone",
  number: "Numéro",
  kind: "Type",
  floor: "Étage",
  area: "Surface",
  shares: "Tantièmes",
  owner: "Copropriétaire",
};
