import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import type { CampaignSurface, PublicSignupCampaign } from "@fitician/core/campaigns";

import { Button, Card } from "../ui/components";
import { fiticianTokens } from "../ui/tokens";

export interface SignupCampaignCardProps {
  readonly campaign: PublicSignupCampaign | null;
  readonly surface: CampaignSurface;
}

export function SignupCampaignCard({ campaign, surface }: SignupCampaignCardProps) {
  const router = useRouter();
  if (campaign === null) return null;

  const title = campaign.public_title_fa;
  const message = campaign.public_message_fa;
  const badge = campaign.public_badge_fa;
  if (title === null || message === null) return null;
  const benefit = campaign.term_weeks === null
    ? `${campaign.duration_days} روز دسترسی مهمان`
    : `${campaign.term_weeks} هفته برنامه تمرین · ${campaign.duration_days} روز دسترسی مهمان`;

  return (
    <Card direction="rtl" style={styles.card} testID="signup-campaign-card" variant="hero">
      <View style={styles.content}>
        {badge !== null && badge.trim() !== "" ? <Text style={styles.badge}>{badge}</Text> : null}
        <Text accessibilityRole="header" style={styles.title}>{title}</Text>
        <Text style={styles.message}>{message}</Text>
        <Text style={styles.benefit}>{benefit}</Text>
        {surface === "landing" && campaign.public_cta_fa !== null && campaign.public_cta_fa.trim() !== "" ? (
          <Button
            label={campaign.public_cta_fa}
            onPress={() => router.push("/public-onboarding")}
            style={styles.cta}
          />
        ) : null}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    marginHorizontal: fiticianTokens.spacing[4],
    marginVertical: fiticianTokens.spacing[3],
  },
  content: {
    flexDirection: "column",
    gap: fiticianTokens.spacing[2],
  },
  badge: {
    alignSelf: "flex-start",
    backgroundColor: fiticianTokens.colors.aqua,
    borderRadius: fiticianTokens.radii.pill,
    color: fiticianTokens.colors.canvas,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
    fontWeight: fiticianTokens.typography.fontWeight.extraBold,
    paddingHorizontal: fiticianTokens.spacing[2],
    paddingVertical: fiticianTokens.spacing[1],
    writingDirection: "rtl",
  },
  title: {
    color: fiticianTokens.colors.mist,
    fontFamily: fiticianTokens.typography.fontFamily.displayPersian,
    fontSize: fiticianTokens.typography.fontSize.h3,
    lineHeight: 28,
    writingDirection: "rtl",
  },
  message: {
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
    lineHeight: 25,
    writingDirection: "rtl",
  },
  benefit: {
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
    writingDirection: "rtl",
  },
  cta: {
    alignSelf: "flex-start",
    marginTop: fiticianTokens.spacing[2],
    minWidth: 168,
  },
});
