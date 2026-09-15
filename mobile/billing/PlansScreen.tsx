import { useEffect, useMemo, useState } from "react";
import { LayoutAnimation, Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";

import {
  billingCategories,
  defaultBillingCategory,
  getBodyAnalysisQuotaEstimate,
  groupBillingOffers,
  isBillingPackageCode,
  packagesForBillingCategory,
  type BillingCategory,
  type BillingPackageCode,
  type EntitlementSnapshot,
} from "@fitician/core";
import fa from "@fitician/core/i18n/fa";
import { formatTehranDate } from "@fitician/core";
import { paymentProviderCodes, type BillingOffer } from "@fitician/core/billing";

import { useMobileAuth } from "../auth/MobileAuthProvider";
import { useMobileEntitlements } from "../entitlements/EntitlementProvider";
import { AppIcon, Button, Card, Notice, PageHeading, Skeleton } from "../ui/components";
import { Screen } from "../ui/layout";
import { mobileRequestErrorMessage } from "../ui/requestState";
import { RTL_ROW, RTL_TEXT } from "../ui/rtl";
import { fiticianTokens } from "../ui/tokens";
import { createBillingApi } from "./billingApi";
import { createPurchaseService } from "./purchaseService";

const billing = fa.translation.billing;
const packageDetails = {
  training: billing.packageDetails.training,
  training_coach: billing.packageDetails.trainingCoach,
  nutrition: billing.packageDetails.nutrition,
  nutrition_physician: billing.packageDetails.nutritionPhysician,
  complete: billing.packageDetails.complete,
  complete_care: billing.packageDetails.completeCare,
} as const;
const packageIcons = {
  training: "training",
  training_coach: "profile",
  nutrition: "nutrition",
  nutrition_physician: "doctor",
  complete: "flash",
  complete_care: "shield",
} as const;

export function PlansScreen() {
  const auth = useMobileAuth();
  const entitlements = useMobileEntitlements();
  const router = useRouter();
  const api = useMemo(() => createBillingApi(auth.request), [auth.request]);
  const purchaseService = useMemo(() => createPurchaseService(api, (url) => Linking.openURL(url)), [api]);
  const [offers, setOffers] = useState<BillingOffer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown | null>(null);
  const [busyOffer, setBusyOffer] = useState<string | null>(null);
  const [message, setMessage] = useState<"success" | "pending" | null>(null);
  const [category, setCategory] = useState<BillingCategory>(() => defaultBillingCategory(entitlements.snapshot?.primary_package));
  const [selectedDurations, setSelectedDurations] = useState<Partial<Record<BillingPackageCode, BillingOffer["duration_weeks"]>>>({});
  const [expandedPackages, setExpandedPackages] = useState<Partial<Record<BillingPackageCode, boolean>>>({});
  const snapshot = entitlements.snapshot;

  useEffect(() => { setCategory(defaultBillingCategory(snapshot?.primary_package)); }, [snapshot?.primary_package]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    void api.getOffers().then((result) => {
      if (!active) return;
      setOffers(result);
      setError(null);
    }).catch((loadError: unknown) => {
      if (active) setError(loadError);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [api]);

  async function buy(offer: BillingOffer) {
    if (!offer.is_available || busyOffer !== null) return;
    setBusyOffer(offer.offer_code);
    setMessage(null);
    setError(null);
    try {
      const order = await api.createOrder({
        client_idempotency_key: `mobile-${offer.offer_code}-${Date.now()}`,
        offer_code: offer.offer_code,
        provider: paymentProviderCodes[0],
      });
      const checkout = await api.createCheckout(order.id, { provider: order.provider });
      const result = await purchaseService.completeCheckout(checkout);
      if (result?.verified) {
        entitlements.refresh();
        setMessage("success");
      } else {
        setMessage("pending");
      }
    } catch (purchaseError) {
      setError(purchaseError);
    } finally {
      setBusyOffer(null);
    }
  }

  const groupedOffers = useMemo(() => groupBillingOffers(offers), [offers]);
  const visiblePackages = packagesForBillingCategory[category].filter((code) => groupedOffers.has(code));

  return (
    <Screen contentWidth="reading" contentContainerStyle={styles.screen}>
      <PageHeading eyebrow={billing.plans} supportingText={billing.pricingSubtitle} title={billing.choosePlan} />
      {snapshot ? <CurrentPackageCard snapshot={snapshot} /> : null}
      <View accessibilityRole="tablist" style={styles.categorySelector}>
        {billingCategories.map((item) => {
          const selected = item === category;
          return (
            <Pressable
              accessibilityLabel={billing.categories[item]}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              key={item}
              onPress={() => setCategory(item)}
              style={({ pressed }) => [styles.categoryButton, selected && styles.categoryButtonSelected, pressed && styles.pressed]}
            >
              <Text style={[styles.categoryLabel, selected && styles.categoryLabelSelected]}>{billing.categories[item]}</Text>
            </Pressable>
          );
        })}
      </View>
      {message === "success" ? <Notice message={billing.accessActive} variant="success" /> : null}
      {message === "pending" ? <Notice message={billing.paymentPending} variant="info" /> : null}
      {error !== null ? <Notice message={mobileRequestErrorMessage(error, billing.loadError, { audience: "member", context: "billing" })} variant="danger" /> : null}
      {loading ? <Skeleton accessibilityLabel={billing.loading} height={180} /> : null}
      {!loading && !error && offers.length === 0 ? <Notice message={billing.noOffers} variant="info" /> : null}
      {!loading && visiblePackages.length > 0 ? (
        <View style={styles.offerList}>
          {visiblePackages.map((packageCode) => {
            const packageOffers = groupedOffers.get(packageCode) ?? [];
            const selectedDuration = selectedDurations[packageCode] ?? packageOffers[0]?.duration_weeks;
            const selectedOffer = packageOffers.find((item) => item.duration_weeks === selectedDuration) ?? packageOffers[0];
            if (!selectedOffer) return null;
            return (
              <PackageCard
                active={snapshot?.primary_package === packageCode}
                busyOffer={busyOffer}
                expanded={expandedPackages[packageCode] ?? false}
                key={packageCode}
                offers={packageOffers}
                onBuy={(item) => void buy(item)}
                onSelectDuration={(duration) => setSelectedDurations((current) => ({ ...current, [packageCode]: duration }))}
                onToggleFeatures={() => {
                  LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
                  setExpandedPackages((current) => ({ ...current, [packageCode]: !current[packageCode] }));
                }}
                packageCode={packageCode}
                selectedOffer={selectedOffer}
              />
            );
          })}
        </View>
      ) : null}
      <Button label={billing.purchaseHistory} onPress={() => router.push("/member/billing-history")} variant="secondary" />
    </Screen>
  );
}

type PackageCardProps = {
  readonly active: boolean;
  readonly busyOffer: string | null;
  readonly expanded: boolean;
  readonly offers: readonly BillingOffer[];
  readonly onBuy: (offer: BillingOffer) => void;
  readonly onSelectDuration: (duration: BillingOffer["duration_weeks"]) => void;
  readonly onToggleFeatures: () => void;
  readonly packageCode: BillingPackageCode;
  readonly selectedOffer: BillingOffer;
};

function PackageCard({ active, busyOffer, expanded, offers, onBuy, onSelectDuration, onToggleFeatures, packageCode, selectedOffer }: PackageCardProps) {
  const details = packageDetails[packageCode];
  const quota = getBodyAnalysisQuotaEstimate(selectedOffer);
  const duration = durationLabel(selectedOffer.duration_weeks);
  const premium = packageCode === "complete_care";
  const featured = packageCode === "complete";

  return (
    <Card style={[styles.offerCard, active && styles.activeCard, featured && styles.featuredCard, premium && styles.premiumCard]} testID={`billing-package-${packageCode}`} variant={premium ? "raised" : "default"}>
      <View style={styles.cardTopline}>
        <View style={[styles.iconContainer, premium && styles.premiumIcon]}><AppIcon color={fiticianTokens.colors.aqua} name={packageIcons[packageCode]} /></View>
        <View style={styles.badgeRow}>
          {active ? <Badge label={billing.activeBadge} success /> : null}
          {details.badge ? <Badge label={details.badge} /> : null}
        </View>
      </View>
      <Text accessibilityRole="header" style={styles.packageName}>{details.name}</Text>
      <Text style={styles.packageSubtitle}>{details.subtitle}</Text>
      <Text style={styles.tagline}>{details.tagline}</Text>
      <View style={styles.features}>
        {(expanded ? details.features : details.features.slice(0, 4)).map((feature) => (
          <View key={feature} style={styles.featureRow}>
            <View style={styles.checkContainer}><AppIcon color={fiticianTokens.colors.aqua} name="check" size={13} /></View>
            <Text style={styles.featureText}>{feature}</Text>
          </View>
        ))}
      </View>
      {details.features.length > 4 ? (
        <Pressable accessibilityLabel={`${expanded ? billing.showFewerFeatures : billing.showAllFeatures} ${details.name}`} accessibilityRole="button" accessibilityState={{ expanded }} onPress={onToggleFeatures} style={({ pressed }) => [styles.featureToggle, pressed && styles.pressed]}>
          <Text style={styles.featureToggleText}>{expanded ? billing.showFewerFeatures : billing.showAllFeatures}</Text>
          <AppIcon color={fiticianTokens.colors.aqua} name={expanded ? "chevronUp" : "chevronDown"} size={18} />
        </Pressable>
      ) : null}
      <View style={styles.purchaseBlock}>
        <Text style={styles.durationEyebrow}>{billing.chooseDuration}</Text>
        <View style={styles.durationSelector}>
          {offers.map((offer) => {
            const label = durationLabel(offer.duration_weeks);
            const selected = offer.offer_code === selectedOffer.offer_code;
            return (
              <Pressable
                accessibilityLabel={interpolate(billing.selectedDuration, { duration: label, package: details.name })}
                accessibilityRole="button"
                accessibilityState={{ selected }}
                key={offer.offer_code}
                onPress={() => onSelectDuration(offer.duration_weeks)}
                style={({ pressed }) => [styles.durationButton, selected && styles.durationButtonSelected, pressed && styles.pressed]}
              >
                <Text style={[styles.durationText, selected && styles.durationTextSelected]}>{label}</Text>
              </Pressable>
            );
          })}
        </View>
        {quota ? (
          <View style={styles.quotaHighlight}>
            <AppIcon color={fiticianTokens.colors.aqua} name="bodyAnalysis" size={18} />
            <Text style={styles.quotaText}>{interpolate(quota.windowDays === 7 ? billing.bodyAnalysisWeeklyQuota : billing.bodyAnalysisQuota, {
              limit: formatNumber(quota.limit), total: formatNumber(quota.estimatedTotal), windowDays: formatNumber(quota.windowDays),
            })}</Text>
          </View>
        ) : null}
        <Text style={styles.offerPrice}>{selectedOffer.price_irr === null || selectedOffer.currency === null ? billing.offerUnavailable : formatAmount(selectedOffer.price_irr, selectedOffer.currency)}</Text>
        {!selectedOffer.is_available ? <Text style={styles.unavailableText}>{billing.offerUnavailable}</Text> : null}
        <Button
          disabled={!selectedOffer.is_available || busyOffer !== null}
          label={interpolate(billing.buySelectedPackage, { duration, package: details.name })}
          loading={busyOffer === selectedOffer.offer_code}
          onPress={() => onBuy(selectedOffer)}
        >
          {billing.buy}
        </Button>
      </View>
    </Card>
  );
}

function CurrentPackageCard({ snapshot }: { readonly snapshot: EntitlementSnapshot }) {
  const now = Date.now();
  const expiry = snapshot.trial.active ? snapshot.trial.ends_at : snapshot.grants
    .filter((grant) => {
      const startsAt = Date.parse(grant.starts_at);
      const endsAt = grant.ends_at === null ? null : Date.parse(grant.ends_at);
      return grant.package_code === snapshot.primary_package && grant.revoked_at === null
        && startsAt <= now && (endsAt === null || endsAt > now);
    })
    .map((grant) => grant.ends_at)
    .filter((value): value is string => value !== null)
    .sort()
    .at(-1);
  const currentPackageName = isBillingPackageCode(snapshot.primary_package)
    ? packageDetails[snapshot.primary_package].name
    : packageLabel(snapshot.primary_package);
  return (
    <Card style={styles.accessCard} variant="hero">
      <View style={styles.currentIcon}><AppIcon color={fiticianTokens.colors.aqua} name="document" /></View>
      <View style={styles.currentCopy}><Text style={styles.accessEyebrow}>{billing.currentPlan}</Text><Text style={styles.accessTitle}>{currentPackageName}</Text></View>
      <View style={styles.currentStatus}><View style={styles.badgeRow}><Badge label={billing.activeBadge} success />{snapshot.trial.active ? <Badge label={billing.trialBadge} /> : null}</View>{expiry ? <Text style={styles.accessSubtitle}>{snapshot.trial.active ? billing.trialExpiration.replace("{{date}}", formatAccessDate(expiry)) : billing.accessEnds.replace("{{date}}", formatAccessDate(expiry))}</Text> : null}</View>
    </Card>
  );
}

function Badge({ label, success = false }: { readonly label: string; readonly success?: boolean }) {
  return <View style={[styles.badge, success && styles.badgeSuccess]}><Text style={[styles.badgeText, success && styles.badgeTextSuccess]}>{label}</Text></View>;
}

function packageLabel(code: EntitlementSnapshot["primary_package"]): string { return fa.translation.entitlements.packageLabels[code]; }
function durationLabel(duration: BillingOffer["duration_weeks"]): string { return duration === 4 ? billing.fourWeeks : duration === 6 ? billing.sixWeeks : billing.eightWeeks; }
function formatNumber(value: number): string { return new Intl.NumberFormat("fa-IR").format(value); }
function formatAmount(amount: number, currency: string): string { return `${formatNumber(amount)} ${currency}`; }
function formatAccessDate(value: string): string { try { return formatTehranDate(value); } catch { return value; } }
function interpolate(template: string, values: Readonly<Record<string, string>>): string { return Object.entries(values).reduce((result, [key, value]) => result.replace(`{{${key}}}`, value), template); }

const styles = StyleSheet.create({
  accessCard: { ...RTL_ROW, alignItems: "center", gap: fiticianTokens.spacing[3], marginTop: fiticianTokens.spacing[4] },
  accessEyebrow: { ...RTL_TEXT, color: fiticianTokens.colors.muted, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.xs },
  accessSubtitle: { ...RTL_TEXT, color: fiticianTokens.colors.muted, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.xs },
  accessTitle: { ...RTL_TEXT, color: fiticianTokens.colors.ink, fontFamily: fiticianTokens.typography.fontFamily.displayPersian, fontSize: fiticianTokens.typography.fontSize.lg },
  activeCard: { borderColor: fiticianTokens.colors.aqua },
  badge: { alignSelf: "flex-start", backgroundColor: fiticianTokens.colors.aquaAtmosphere, borderColor: fiticianTokens.colors.lineStrong, borderRadius: fiticianTokens.radii.pill, borderWidth: 1, paddingHorizontal: fiticianTokens.spacing[2], paddingVertical: fiticianTokens.spacing[1] },
  badgeRow: { ...RTL_ROW, flexWrap: "wrap", gap: fiticianTokens.spacing[1] },
  badgeSuccess: { backgroundColor: fiticianTokens.colors.successSurface, borderColor: fiticianTokens.colors.success },
  badgeText: { ...RTL_TEXT, color: fiticianTokens.colors.aqua, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.xs, fontWeight: fiticianTokens.typography.fontWeight.bold },
  badgeTextSuccess: { color: fiticianTokens.colors.success },
  cardTopline: { ...RTL_ROW, alignItems: "flex-start", justifyContent: "space-between" },
  categoryButton: { alignItems: "center", borderColor: "transparent", borderRadius: fiticianTokens.radii.pill, borderWidth: 1, flex: 1, minHeight: fiticianTokens.layout.minimumTouchTarget, justifyContent: "center" },
  categoryButtonSelected: { backgroundColor: fiticianTokens.colors.aqua, borderColor: fiticianTokens.colors.aqua },
  categoryLabel: { ...RTL_TEXT, color: fiticianTokens.colors.muted, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.sm, fontWeight: fiticianTokens.typography.fontWeight.bold },
  categoryLabelSelected: { color: fiticianTokens.colors.canvas },
  categorySelector: { ...RTL_ROW, backgroundColor: fiticianTokens.colors.surfaceSubtle, borderColor: fiticianTokens.colors.line, borderRadius: fiticianTokens.radii.pill, borderWidth: 1, gap: fiticianTokens.spacing[1], marginTop: fiticianTokens.spacing[4], padding: fiticianTokens.spacing[1] },
  checkContainer: { alignItems: "center", backgroundColor: fiticianTokens.colors.aquaAtmosphere, borderColor: fiticianTokens.colors.lineStrong, borderRadius: fiticianTokens.radii.pill, borderWidth: 1, height: 20, justifyContent: "center", marginTop: 2, width: 20 },
  currentCopy: { flex: 1, gap: fiticianTokens.spacing[1] },
  currentIcon: { alignItems: "center", backgroundColor: fiticianTokens.colors.aquaAtmosphere, borderRadius: fiticianTokens.radii.medium, height: 44, justifyContent: "center", width: 44 },
  currentStatus: { alignItems: "flex-end", gap: fiticianTokens.spacing[2] },
  durationButton: { alignItems: "center", backgroundColor: fiticianTokens.colors.surfaceSubtle, borderColor: fiticianTokens.colors.line, borderRadius: fiticianTokens.radii.small, borderWidth: 1, flex: 1, justifyContent: "center", minHeight: fiticianTokens.layout.minimumTouchTarget },
  durationButtonSelected: { backgroundColor: fiticianTokens.colors.aquaAtmosphere, borderColor: fiticianTokens.colors.aqua },
  durationEyebrow: { ...RTL_TEXT, color: fiticianTokens.colors.muted, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.xs },
  durationSelector: { ...RTL_ROW, gap: fiticianTokens.spacing[2] },
  durationText: { ...RTL_TEXT, color: fiticianTokens.colors.muted, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.sm, fontWeight: fiticianTokens.typography.fontWeight.bold },
  durationTextSelected: { color: fiticianTokens.colors.ink },
  featureRow: { ...RTL_ROW, alignItems: "flex-start", gap: fiticianTokens.spacing[2] },
  featureText: { ...RTL_TEXT, color: fiticianTokens.colors.muted, flex: 1, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.sm, lineHeight: 23 },
  featureToggle: { ...RTL_ROW, alignItems: "center", alignSelf: "flex-start", gap: fiticianTokens.spacing[1], minHeight: fiticianTokens.layout.minimumTouchTarget },
  featureToggleText: { ...RTL_TEXT, color: fiticianTokens.colors.aqua, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.sm, fontWeight: fiticianTokens.typography.fontWeight.bold },
  featuredCard: { backgroundColor: fiticianTokens.colors.infoSurface, borderColor: fiticianTokens.colors.lineStrong },
  features: { gap: fiticianTokens.spacing[2] },
  iconContainer: { alignItems: "center", backgroundColor: fiticianTokens.colors.aquaAtmosphere, borderColor: fiticianTokens.colors.lineStrong, borderRadius: fiticianTokens.radii.medium, borderWidth: 1, height: 48, justifyContent: "center", width: 48 },
  offerCard: { gap: fiticianTokens.spacing[3], overflow: "hidden" },
  offerList: { gap: fiticianTokens.spacing[4], marginVertical: fiticianTokens.spacing[4] },
  offerPrice: { color: fiticianTokens.colors.ink, fontFamily: fiticianTokens.typography.fontFamily.bodyEnglish, fontSize: fiticianTokens.typography.fontSize.h3, fontWeight: fiticianTokens.typography.fontWeight.extraBold, writingDirection: "ltr" },
  packageName: { ...RTL_TEXT, color: fiticianTokens.colors.ink, fontFamily: fiticianTokens.typography.fontFamily.displayPersian, fontSize: fiticianTokens.typography.fontSize.h2 },
  packageSubtitle: { ...RTL_TEXT, color: fiticianTokens.colors.muted, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.sm, lineHeight: 24 },
  premiumCard: { borderColor: fiticianTokens.colors.aqua, shadowColor: fiticianTokens.shadows.glow.color, shadowOffset: fiticianTokens.shadows.glow.offset, shadowOpacity: fiticianTokens.shadows.glow.opacity, shadowRadius: fiticianTokens.shadows.glow.radius },
  premiumIcon: { backgroundColor: fiticianTokens.colors.surfaceInteractive },
  pressed: { opacity: 0.82 },
  purchaseBlock: { borderTopColor: fiticianTokens.colors.line, borderTopWidth: 1, gap: fiticianTokens.spacing[3], paddingTop: fiticianTokens.spacing[4] },
  quotaHighlight: { ...RTL_ROW, alignItems: "center", backgroundColor: fiticianTokens.colors.infoSurface, borderColor: fiticianTokens.colors.lineStrong, borderRadius: fiticianTokens.radii.medium, borderWidth: 1, gap: fiticianTokens.spacing[2], padding: fiticianTokens.spacing[3] },
  quotaText: { ...RTL_TEXT, color: fiticianTokens.colors.ink, flex: 1, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.xs, lineHeight: 20 },
  screen: { gap: fiticianTokens.spacing[3] },
  tagline: { ...RTL_TEXT, color: fiticianTokens.colors.ink, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.sm, fontWeight: fiticianTokens.typography.fontWeight.bold, lineHeight: 24 },
  unavailableText: { ...RTL_TEXT, color: fiticianTokens.colors.muted, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.xs },
});
