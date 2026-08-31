export type UserRole = "admin" | "member";

export interface UserSummary {
  id: string;
  name: string;
  email: string;
  role: UserRole;
}

export interface OrganizationSummary {
  id: string;
  name: string;
  slug: string;
}

export interface MeResponse {
  user: UserSummary;
  organization: OrganizationSummary;
}
