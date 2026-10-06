// Match route shapes, not arbitrary prefixes. Shared by build, Workbox and HTTP tests.
export const memberRouteSources = [
  "(?:login|register|forgot-password|reset-password|verify-email|get-started|delete-account|onboarding|dashboard|profile|more|plans|notifications|progress|nutrition-profile|nutrition-estimate|nutrition-tracking|nutrition-labs|nutrition-supplements|food-catalogue|meal-catalogue|workout-plan)",
  "exercises(?:/[a-z0-9]+(?:-[a-z0-9]+)*)?",
  "body-progress(?:/(?:new|[a-zA-Z0-9-]+))?",
  "conversation/(?:workout|nutrition)/[a-zA-Z0-9-]+",
  "support/(?:new|tickets(?:/[a-zA-Z0-9-]+)?)",
  "billing/(?:history|result|checkout-result|checkout/[^/]+)",
  "(?:coach/workouts|physician/nutrition)",
  "admin/(?:support(?:/[^/]+)?|ai-settings|nutrition-supplements|nutrition-monitoring|exercises(?:/new|/[^/]+/edit)?|nutrition-meals(?:/new|/[^/]+/edit)?|nutrition-programs(?:/new|/[^/]+/edit)?|training-program-templates(?:/new|/[^/]+/edit)?|training-program-structures(?:/new|/[^/]+/edit)?|billing(?:/(?:offers|campaigns|users(?:/[^/]+)?|orders(?:/[^/]+)?|audit))?)",
];
export const memberNavigationPattern = new RegExp(`^/(?:${memberRouteSources.join("|")})/?(?:\\?.*)?$`);
