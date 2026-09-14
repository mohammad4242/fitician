import { useEffect, useMemo, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import fa from "@fitician/core/i18n/fa";
import { formatTehranDate } from "@fitician/core";
import type { BillingOrder } from "@fitician/core/billing";

import { useMobileAuth } from "../auth/MobileAuthProvider";
import { Card, Notice, PageHeading, Skeleton } from "../ui/components";
import { Screen } from "../ui/layout";
import { RTL_TEXT } from "../ui/rtl";
import { fiticianTokens } from "../ui/tokens";
import { createBillingApi } from "./billingApi";

const billing = fa.translation.billing;

export function BillingHistoryScreen() {
  const auth = useMobileAuth();
  const api = useMemo(() => createBillingApi(auth.request), [auth.request]);
  const [orders, setOrders] = useState<BillingOrder[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let active = true;
    void api.getOrders()
      .then((result) => {
        if (!active) return;
        setOrders(result);
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => { active = false; };
  }, [api]);

  return (
    <Screen contentWidth="reading" contentContainerStyle={styles.screen}>
      <PageHeading eyebrow={billing.manageAccess} title={billing.purchaseHistory} />
      {state === "loading" ? <Skeleton accessibilityLabel={billing.loading} height={150} /> : null}
      {state === "error" ? <Notice message={billing.historyError} variant="danger" /> : null}
      {state === "ready" && orders.length === 0 ? <Notice message={billing.noOffers} variant="info" /> : null}
      {state === "ready" && orders.length > 0 ? (
        <View style={styles.list}>
          {orders.map((order) => (
            <Card key={order.id} style={styles.orderCard}>
              <View style={styles.orderRow}>
                <View style={styles.orderCopy}>
                  <Text style={styles.package}>{packageLabel(order.package_code_snapshot)}</Text>
                  <Text style={styles.detail}>{durationLabel(order.duration_weeks_snapshot)} · {order.offer_code}</Text>
                </View>
                <Text style={styles.amount}>{formatAmount(order.amount_irr_snapshot, order.currency_snapshot)}</Text>
              </View>
              <View style={styles.orderRow}>
                <Text style={styles.detail}>{statusLabel(order.status)}</Text>
                <Text style={styles.date}>{formatDate(order.created_at)}</Text>
              </View>
            </Card>
          ))}
        </View>
      ) : null}
    </Screen>
  );
}

function packageLabel(code: BillingOrder["package_code_snapshot"]): string {
  return fa.translation.entitlements.packageLabels[code];
}

function durationLabel(duration: BillingOrder["duration_weeks_snapshot"]): string {
  if (duration === 4) return billing.fourWeeks;
  if (duration === 6) return billing.sixWeeks;
  return billing.eightWeeks;
}

function statusLabel(status: BillingOrder["status"]): string {
  if (status === "paid") return billing.paymentSuccessful;
  if (status === "pending") return billing.paymentPending;
  if (status === "failed") return billing.paymentFailed;
  if (status === "cancelled") return billing.paymentCancelled;
  if (status === "refunded") return billing.refund;
  return status;
}

function formatAmount(amount: number, currency: string): string {
  return `${new Intl.NumberFormat("fa-IR").format(amount)} ${currency}`;
}

function formatDate(value: string): string {
  try {
    return formatTehranDate(value);
  } catch {
    return value;
  }
}

const styles = StyleSheet.create({
  amount: {
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.body,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
    writingDirection: "ltr",
  },
  date: {
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
  },
  detail: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
  },
  list: {
    gap: fiticianTokens.spacing[3],
    marginTop: fiticianTokens.spacing[4],
  },
  orderCard: {
    gap: fiticianTokens.spacing[3],
  },
  orderCopy: {
    alignItems: "stretch",
    flex: 1,
    gap: fiticianTokens.spacing[1],
  },
  orderRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: fiticianTokens.spacing[3],
    justifyContent: "space-between",
  },
  package: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.displayPersian,
    fontSize: fiticianTokens.typography.fontSize.lg,
  },
  screen: {
    gap: fiticianTokens.spacing[3],
  },
});
