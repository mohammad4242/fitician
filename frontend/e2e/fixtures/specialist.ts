import { randomUUID } from "node:crypto";
import { execFile } from "node:child_process";
import { dirname, resolve } from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

import type {
  APIRequestContext,
  APIResponse,
  Browser,
  BrowserContext,
  Page,
} from "@playwright/test";

const execFileAsync = promisify(execFile);
const fixtureDirectory = dirname(fileURLToPath(import.meta.url));
const backendDirectory = resolve(fixtureDirectory, "../../../backend");

export const E2E_BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:4173";
const E2E_DATABASE_URL = process.env.E2E_DATABASE_URL
  ?? "postgresql+psycopg://fitician:fitician@127.0.0.1:5432/fitician_e2e";
const E2E_PASSWORD = "E2eTestPassw0rd!";

type FetchOptions = NonNullable<Parameters<APIRequestContext["fetch"]>[1]>;

export type SpecialistRole = "coach" | "physician" | "doctor";

export type E2EAccount = {
  context: BrowserContext;
  page: Page;
  email: string;
  password: string;
  userId: string;
  displayName: string;
};

type AccountOptions = {
  displayName?: string;
  role?: SpecialistRole;
  admin?: boolean;
  packageCode?: string;
};

function requestHeaders(headers: FetchOptions["headers"] | undefined, hasData: boolean) {
  const normalized = new Headers(headers);
  normalized.set("Accept", "application/json");
  normalized.set("Origin", E2E_BASE_URL);
  if (hasData && !normalized.has("Content-Type")) normalized.set("Content-Type", "application/json");
  return Object.fromEntries(normalized.entries());
}

export async function apiResponse(
  context: BrowserContext,
  path: string,
  options: FetchOptions = {},
): Promise<APIResponse> {
  return context.request.fetch(`${E2E_BASE_URL}${path}`, {
    ...options,
    headers: requestHeaders(options.headers, options.data !== undefined),
  });
}

export async function apiJson<T>(
  context: BrowserContext,
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const response = await apiResponse(context, path, options);
  const body = await response.text();
  if (!response.ok()) {
    throw new Error(`${options.method ?? "GET"} ${path} failed with ${response.status()}: ${body}`);
  }
  return JSON.parse(body) as T;
}

async function prepareE2EUser(
  email: string,
  options: AccountOptions,
): Promise<{ id: string }> {
  const args = [
    "run",
    "python",
    "-m",
    "scripts.e2e_fixture",
    "prepare-user",
    "--email",
    email,
    "--package",
    options.packageCode ?? "complete_care",
  ];
  if (options.role !== undefined) {
    args.push("--role", options.role);
    if (options.displayName !== undefined) args.push("--display-name", options.displayName);
  }
  if (options.admin === true) args.push("--admin");

  const result = await execFileAsync("uv", args, {
    cwd: backendDirectory,
    env: { ...process.env, E2E_DATABASE_URL },
    maxBuffer: 1024 * 1024,
  });
  const output = result.stdout.trim();
  try {
    return JSON.parse(output) as { id: string };
  } catch {
    throw new Error(`E2E fixture did not return JSON for ${email}: ${output}`);
  }
}

export async function createE2EAccount(
  browser: Browser,
  label: string,
  options: AccountOptions = {},
): Promise<E2EAccount> {
  const context = await browser.newContext();
  await context.addInitScript(() => {
    window.localStorage.setItem("fitician-language", "fa");
  });
  const email = `${label}-${randomUUID()}@example.com`;
  await apiJson<{ id: string }>(context, "/api/v1/auth/register", {
    method: "POST",
    data: { email, password: E2E_PASSWORD },
  });
  const prepared = await prepareE2EUser(email, options);
  const current = await apiJson<{ id: string }>(context, "/api/v1/auth/me");
  if (current.id !== prepared.id) throw new Error(`E2E fixture user mismatch for ${email}`);
  const page = await context.newPage();
  return {
    context,
    page,
    email,
    password: E2E_PASSWORD,
    userId: current.id,
    displayName: options.displayName ?? label,
  };
}

export async function setupWorkoutMember(context: BrowserContext, displayName: string) {
  await apiJson(context, "/api/v1/profile/mode", {
    method: "POST",
    data: { product_mode: "training" },
  });
  await apiJson(context, "/api/v1/profile", {
    method: "POST",
    data: {
      display_name: displayName,
      birth_date: "2000-05-14",
      sex: "male",
      height_cm: 178,
      current_weight_kg: 76.5,
      fitness_goal: "build_muscle",
      experience_level: "beginner",
      training_days_per_week: 2,
      training_location: "gym",
      training_cautions: [],
      plan_duration_weeks: 4,
      workout_generation_method: "fitician_coach",
      session_duration_minutes: 45,
      training_intensity: "moderate",
    },
  });
}

export async function setupNutritionMember(
  context: BrowserContext,
  displayName: string,
  medicalDetails: string,
) {
  await apiJson(context, "/api/v1/profile/mode", {
    method: "POST",
    data: { product_mode: "nutrition" },
  });
  await apiJson(context, "/api/v1/profile/shared", {
    method: "PUT",
    data: {
      display_name: displayName,
      birth_date: "1998-05-14",
      sex: "female",
      height_cm: 165,
      current_weight_kg: 62.5,
      fitness_goal: "maintain_weight",
    },
  });
  await apiJson(context, "/api/v1/nutrition/safety", {
    method: "PUT",
    data: {
      conditions: [{ code: "controlled_hypertension", details: medicalDetails }],
      medications: [],
      dangerous_food_reaction_history: false,
      pregnant: false,
      breastfeeding: false,
      eating_disorder_diagnosed: false,
      eating_disorder_active_symptoms: false,
      emergency_or_danger_symptoms: false,
      complex_medication_food_interaction: false,
      physician_dietary_restrictions: null,
      other_relevant_condition: null,
    },
  });
  await apiJson(context, "/api/v1/nutrition/profile", {
    method: "PUT",
    data: {
      daily_activity_level: "sedentary",
      individual_monthly_food_budget_irr: 100_000_000,
      budget_style: "strict",
      meals_per_day: 2,
      snacks_per_day: 1,
      preferred_plan_start_day: "saturday",
      plan_style: "balanced",
      cooking_skill: "basic",
      maximum_cooking_time_minutes: 45,
      cooking_frequency_per_week: 4,
      meal_preparation_preference: "mixed",
      refrigerator_access: true,
      freezer_access: true,
      cooking_equipment: ["stove"],
      supplied_meals_per_week: 0,
      supplied_meal_source: null,
      foods_available_at_home: [],
      favourite_foods: [],
      disliked_foods: [],
      never_suggest_foods: [],
      refused_foods: [],
      allergies: [],
      intolerances: [],
      dietary_pattern: "omnivore",
      religious_cultural_exclusions: [],
      preferred_variety: "medium",
      maximum_meal_repetition_per_week: 2,
      accepts_leftovers: true,
      accepts_batch_cooking: true,
      work_shift_context: null,
      daily_check_in_enabled: false,
      preferred_check_in_time: null,
    },
  });
  await apiJson(context, "/api/v1/nutrition/structured-exercise", {
    method: "PUT",
    data: { trains: false },
  });
  await apiJson(context, "/api/v1/nutrition/estimates", { method: "POST" });
}
