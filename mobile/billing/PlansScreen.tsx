import { useEffect, useMemo, useState } from "react";
import { Linking, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";

import fa from "@fitician/core/i18n/fa";
import type { BillingOffer } from "@fitician/core/billing";

import { useMobileAuth } from "../auth/MobileAuthProvider";
import { useMobileEntitlements } from "../entitlements/EntitlementProvider";
import { Button, Card, Notice, PageHeading, Skeleton } from "../ui/components";
import { Screen } from "../ui/layout";
import { RTL_TEXT } from "../ui/rtl";
import { fiticianTokens } from "../ui/tokens";
import { createBillingApi } from "./billingApi";
import { createPurchaseService } from "./purchaseService";

const billing = fa.translation.billing;

export function PlansScreen() {
  const auth = useMobileAuth();
  const entitlements = useMobileEntitlements();
  const router = useRouter();
  const api = useMemo(() => createBillingApi(auth.request), [auth.request]);
  const purchaseService = useMemo(
    () => createPurchaseService(api, (url) => Linking.openURL(url)),
    [api],
  );
  const [offers, setOffers] = useState<BillingOffer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [busyOffer, setBusyOffer] = useState<string | null>(null);
  const [message, setMessage] = useState<"success" | "pending" | null>(null);
  const snapshot = entitlements.snapshot;

  useEffect(() => {
    let active = true;
    setLoading(true);
    void api.getOffers()
      .then((result) => {
        if (!active) return;
        setOffers(result);
        setError(false);
      })
      .catch(() => {
        if (active) setError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [api]);

  async function buy(offer: BillingOffer) {
    if (!offer.is_available || busyOffer !== null) return;
    setBusyOffer(offer.offer_code);
    setMessage(null);
    setError(false);
    try {
      const order = await api.createOrder({
        client_idempotency_key: `mobile-${offer.offer_code}-${Date.now()}`,
        offer_code: offer.offer_code,
        provider: "fake",
      });
      const checkout = await api.createCheckout(order.id, { provider: order.provider });
      const result = await purchaseService.completeCheckout(checkout);
      if (result?.verified) {
        entitlements.refresh();
        setMessage("success");
      } else {
        setMessage("pending");
      }
    } catch {
      setError(true);
    } finally {
      setBusyOffer(null);
    }
  }

  return (
    <Screen contentWidth="reading" contentContainerStyle={styles.screen}>
      <PageHeading
        eyebrow={billing.plans}
        supportingText={billing.chooseDuration}
        title={billing.choosePlan}
      />
      {snapshot ? (
        <Card style={styles.accessCard}>
          <Text style={styles.accessEyebrow}>{billing.currentPlan}</Text>
          <Text style={styles.accessTitle}>{packageLabel(snapshot.primary_package)}</Text>
          {snapshot.trial.active && snapshot.trial.ends_at ? (
            <Text style={styles.accessSubtitle}>{fa.translation.entitlements.trialActive} · تا {formatAccessDate(snapshot.trial.ends_at)}</Text>
          ) : null}
        </Card>
      ) : null}
      {message === "success" ? <Notice message={billing.accessActive} variant="success" /> : null}
      {message === "pending" ? <Notice message={billing.paymentPending} variant="info" /> : null}
      {error ? <Notice message={billing.loadError} variant="danger" /> : null}
      {loading ? <Skeleton accessibilityLabel={billing.loading} height={180} /> : null}
      {!loading && !error && offers.length === 0 ? <Notice message={billing.noOffers} variant="info" /> : null}
      {!loading && offers.length > 0 ? (
        <View style={styles.offerList}>
          {offers.map((offer) => (
            <Card key={offer.offer_code} style={[styles.offerCard, !offer.is_available && styles.unavailable]} testID={`billing-offer-${offer.offer_code}`}>
              <View style={styles.offerHeader}>
                <View style={styles.offerCopy}>
                  <Text style={styles.offerPackage}>{packageLabel(offer.package_code)}</Text>
                  <Text style={styles.offerDuration}>{durationLabel(offer.duration_weeks)}</Text>
                </View>
                <Text style={styles.offerPrice}>
                  {offer.price_irr === null || offer.currency === null
                    ? billing.offerUnavailable
                    : formatAmount(offer.price_irr, offer.currency)}
                </Text>
              </View>
              {!offer.is_available ? <Text style={styles.unavailableText}>{billing.offerUnavailable}</Text> : null}
              <Button
                disabled={!offer.is_available || busyOffer !== null}
                label={`${billing.buy} ${durationLabel(offer.duration_weeks)}`}
                loading={busyOffer === offer.offer_code}
                onPress={() => void buy(offer)}
              />
            </Card>
          ))}
        </View>
      ) : null}
      <Button label={billing.purchaseHistory} onPress={() => router.push("/member/billing-history")} variant="secondary" />
    </Screen>
  );
}

function packageLabel(code: BillingOffer["package_code"]): string {
  return fa.translation.entitlements.packageLabels[code];
}

function durationLabel(duration: BillingOffer["duration_weeks"]): string {
  if (duration === 4) return billing.fourWeeks;
  if (duration === 6) return billing.sixWeeks;
  return billing.eightWeeks;
}

function formatAmount(amount: number, currency: string): string {
  return `${new Intl.NumberFormat("fa-IR").format(amount)} ${currency}`;
}

function formatAccessDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("fa-IR", { dateStyle: "medium" }).format(date);
}

const styles = StyleSheet.create({
  accessCard: {
    gap: fiticianTokens.spacing[1],
    marginTop: fiticianTokens.spacing[4],
  },
  accessEyebrow: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
  },
  accessSubtitle: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
  },
  accessTitle: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.displayPersian,
    fontSize: fiticianTokens.typography.fontSize.lg,
  },
  offerCard: {
    gap: fiticianTokens.spacing[3],
  },
  offerCopy: {
    alignItems: "stretch",
    flex: 1,
    gap: fiticianTokens.spacing[1],
  },
  offerDuration: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.displayPersian,
    fontSize: fiticianTokens.typography.fontSize.h3,
  },
  offerHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: fiticianTokens.spacing[3],
    justifyContent: "space-between",
  },
  offerList: {
    gap: fiticianTokens.spacing[3],
    marginVertical: fiticianTokens.spacing[4],
  },
  offerPackage: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
  },
  offerPrice: {
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.body,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
    writingDirection: "ltr",
  },
  screen: {
    gap: fiticianTokens.spacing[3],
  },
  unavailable: {
    opacity: 0.58,
  },
  unavailableText: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
  },
});
