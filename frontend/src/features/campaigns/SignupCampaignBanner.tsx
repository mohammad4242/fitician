import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { CampaignSurface, PublicSignupCampaign } from "@fitician/core/campaigns";

import { getActiveSignupCampaign } from "./publicCampaignApi";
import "./signupCampaign.css";

type SignupCampaignBannerProps = {
  surface: CampaignSurface;
};

export function SignupCampaignBanner({ surface }: SignupCampaignBannerProps) {
  const { i18n, t } = useTranslation();
  const [campaign, setCampaign] = useState<PublicSignupCampaign | null>(null);

  useEffect(() => {
    let active = true;
    setCampaign(null);
    void getActiveSignupCampaign(surface)
      .then((result) => {
        if (active) setCampaign(result);
      })
      .catch(() => {
        if (active) setCampaign(null);
      });
    return () => {
      active = false;
    };
  }, [surface]);

  if (campaign === null) return null;

  const english = i18n.resolvedLanguage === "en";
  const title = english ? campaign.public_title_en : campaign.public_title_fa;
  const message = english ? campaign.public_message_en : campaign.public_message_fa;
  const cta = english ? campaign.public_cta_en : campaign.public_cta_fa;
  const badge = english ? campaign.public_badge_en : campaign.public_badge_fa;
  if (title === null || message === null) return null;

  const benefit = campaign.term_weeks === null
    ? t("publicCampaign.benefitDays", { count: campaign.duration_days })
    : t("publicCampaign.benefitWeeks", {
      count: campaign.term_weeks,
      days: campaign.duration_days,
    });

  return (
    <aside className={`signup-campaign-banner signup-campaign-banner--${surface}`} data-testid="signup-campaign-banner">
      <div className="signup-campaign-banner__copy">
        {badge !== null && badge.trim() !== "" && <span className="signup-campaign-banner__badge">{badge}</span>}
        <h2>{title}</h2>
        <p>{message}</p>
        <span className="signup-campaign-banner__benefit">{benefit}</span>
      </div>
      {surface === "landing" && cta !== null && cta.trim() !== "" && (
        <Link className="signup-campaign-banner__cta" to="/get-started">
          {cta}
        </Link>
      )}
    </aside>
  );
}
