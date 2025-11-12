import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Field mapping helpers between Convex-style keys and FastAPI-style keys.
const convexToFastApiMap: Record<string, string> = {
  _id: "id",
  _creationTime: "created_at",
  firstName: "first_name",
  lastName: "last_name",
  employeeId: "employee_id",
  checkIn: "check_in",
  checkOut: "check_out",
  workHours: "work_hours",
  leaveType: "leave_type",
};

const fastApiToConvexMap: Record<string, string> = Object.fromEntries(
  Object.entries(convexToFastApiMap).map(([k, v]) => [v, k])
);

function mapKeys(obj: Record<string, any>, keyMap: Record<string, string>): any {
  if (obj == null || typeof obj !== "object") return obj;
  if (Array.isArray(obj)) return obj.map((o) => (typeof o === "object" ? mapKeys(o, keyMap) : o));
  const out: Record<string, any> = {};
  for (const [key, value] of Object.entries(obj)) {
    const mapped = keyMap[key] ?? key;
    out[mapped] = value;
  }
  return out;
}

export function mapConvexToFastApi<T = any>(data: T): T {
  if (Array.isArray(data)) return data.map((d) => mapConvexToFastApi(d)) as any;
  if (data == null || typeof data !== "object") return data;
  return mapKeys(data as any, convexToFastApiMap) as any;
}

export function mapFastApiToConvex<T = any>(data: T): T {
  if (Array.isArray(data)) return data.map((d) => mapFastApiToConvex(d)) as any;
  if (data == null || typeof data !== "object") return data;
  return mapKeys(data as any, fastApiToConvexMap) as any;
}

export { convexToFastApiMap, fastApiToConvexMap };
