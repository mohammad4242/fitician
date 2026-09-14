export const FITICIAN_CORE_VERSION = "0.1.0";

export {
  accessPackageCodes,
  accessPackageKinds,
  entitlementCodes,
  grantSources,
} from "./entitlements";
export type {
  AccessGrantSummary,
  AccessPackageCode,
  AccessPackageKind,
  EntitlementCode,
  EntitlementSnapshot,
  EntitlementState,
  GrantSource,
  ProductCatalogItem,
  ProductQuotaPolicy,
  QuotaStatus,
} from "./entitlements";

export {
  billingOfferCodes,
  billingOrderStatuses,
  billingTransactionStatuses,
  paymentProviderCodes,
} from "./billing";
export type {
  BillingCheckout,
  BillingOffer,
  BillingOfferCode,
  BillingOrder,
  BillingOrderStatus,
  BillingPaymentResult,
  BillingTransactionStatus,
  PaymentProviderCode,
} from "./billing";

export type { components, paths, webhooks } from "./generated/api";
export { localIsoDate, resolvedIanaTimeZone } from "./local-date";
export {
  FITICIAN_WEEKDAY_LABELS_FA,
  IRAN_TIME_ZONE,
  PERSIAN_MONTH_NAMES_FA,
  PERSIAN_CALENDAR_LOCALE,
  daysInJalaliMonth,
  fiticianWeekdayFromIsoDate,
  formatIsoDate,
  formatPersianDate,
  formatPersianDateWithWeekday,
  formatPersianWeekday,
  formatTehranDate,
  formatTehranDateForLocale,
  formatTehranDateTime,
  formatTehranDateTimeForLocale,
  formatTehranTime,
  formatTehranTimeForLocale,
  isValidJalaliDate,
  isoDateToJalaliParts,
  isoTimestampToTehranJalaliParts,
  jalaliPartsToIsoDate,
  tehranJalaliDateTimeToIso,
} from "./iran-calendar";
export type { JalaliDateParts, JalaliDateTimeParts } from "./iran-calendar";
export type {
  NutritionPlanStartRequest,
  NutritionTimelineState,
  ProgramTimelineToday,
  TimezoneResponse,
  TimezoneUpdateRequest,
  TimelineNutrition,
  TimelineWorkout,
  TimelineWorkoutSession,
  WorkoutCycleSessionRescheduleRequest,
  WorkoutCycleSessionStatus,
  WorkoutCycleStartRequest,
  WorkoutTimelineState,
} from "./program-timeline";
export {
  formatPrescriptionTarget,
  formatTomanInput,
  irrToRoundedToman,
  irrToToman,
  roundToTenThousandToman,
  tomanToIrr,
} from "./formatters";
export {
  GHOST_BACK_PRIVACY_CUT_RATIO,
  GHOST_PRIVACY_CUT_RATIO,
  GHOST_SIDE_PRIVACY_CUT_RATIO,
  clampGhostScale,
  getGhostGeometry,
  ghostAssetCalibrationForView,
  ghostAssetVisibleTopRatioForView,
  ghostPrivacyCutRatioForView,
  ghostPrivacyLineGeometry,
  isPointInZone,
  pointZoneDistance,
  transformGhostPoint,
  transformGhostZone,
} from "./body-ghost";
export type {
  GhostAssetCalibration,
  GhostPoint,
  GhostPrivacyLine,
  GhostOverlayVariant,
  GhostViewGeometry,
  GhostZone,
} from "./body-ghost";
export { normalizeBodySegmentationMask } from "./body-photos";
export type { BodySegmentationMask } from "./body-photos";
export {
  GHOST_SCALE_MAX,
  GHOST_SCALE_MIN,
  GHOST_SCALE_STEP,
  PHOTO_SCALE_MAX,
  PHOTO_SCALE_MIN,
  PHOTO_SCALE_STEP,
  stepGhostScale,
} from "./body-ghost-scale";
export {
  GHOST_EDITOR_DEFAULT_TRANSFORM,
  GHOST_EDITOR_OUTPUT,
  GHOST_EDITOR_TOLERANCE,
  clampGhostPhotoTransform,
  containImageRect,
  createGhostPhotoRenderPlan,
  isGhostFramingWithinTolerance,
  privacyCropSourceYForView,
} from "./body-ghost-editor";
export type {
  GhostContainedImageRect,
  GhostDisplaySize,
  GhostPhotoRenderPlan,
  GhostPhotoTransform,
} from "./body-ghost-editor";
export { validatePoseWithGhost } from "./body-ghost-pose";
export type {
  GhostPoseValidationResult,
  GhostPoseValidatorOptions,
  GhostValidationComponentScores,
  GhostValidationHardRejectCode,
  GhostValidationWarning,
  NormalizedBodyLandmark,
} from "./body-ghost-pose";
export type * from "./profile-validation";
export {
  canTransitionOnboardingState,
  createInitialOnboardingState,
  deserializeOnboardingState,
  getOnboardingSteps,
  isOnboardingState,
  serializeOnboardingState,
  transitionOnboardingState,
  OnboardingTransitionError,
} from "./onboarding";
export type {
  NutritionBasicsDraft,
  OnboardingDraftLoadResult,
  OnboardingEvent,
  OnboardingState,
  OnboardingStateStore,
  OnboardingStep,
  OnboardingTransitionErrorCode,
} from "./onboarding";
export { groupReviewQueueByRecency, groupWorkoutReviewQueue } from "./workout-reviews";
export type {
  CoachTemplateSelection,
  ReviewProfileSummary,
  RecencyQueueGroup,
  WorkoutReviewDayDraft,
  WorkoutReviewDetail,
  WorkoutReviewDraftUpdate,
  WorkoutReviewExerciseDraft,
  WorkoutReviewQueueGroup,
  WorkoutReviewQueueItem,
  WorkoutReviewQueueTimestamp,
  WorkoutReviewQueueView,
  WorkoutReviewStatus,
} from "./workout-reviews";
export {
  reviewDisclosureDefaultExpanded,
  reviewDisclosureDefaults,
  reviewDisclosureKeys,
} from "./review-disclosures";
export type { ReviewDisclosureKey } from "./review-disclosures";
export type {
  MobileAuthTokens,
  RefreshTokenStorage,
} from "./auth";
export {
  clampNutritionProgress,
  nutritionTargetToExpenditureRatio,
  nutritionProgressTone,
} from "./nutrition-progress";
export type { NutritionProgressTone } from "./nutrition-progress";
export { ApiError } from "./transport";
export type {
  ApiErrorObject,
  ApiErrorPayload,
  ApiValidationDetail,
  BinaryDownload,
  BinaryDownloadRequest,
  CancellationSignal,
  CursorPage,
  FiticianTransport,
  HttpMethod,
  JsonObject,
  JsonPrimitive,
  JsonValue,
  MultipartPart,
  MultipartUploadRequest,
  Page,
  RequestHeaders,
  TransportRequest,
} from "./transport";
