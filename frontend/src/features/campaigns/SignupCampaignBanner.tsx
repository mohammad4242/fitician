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
  const { i18n } = useTranslation();
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
  const completePackage = campaign.package_code === "complete" || campaign.package_code === "complete_care";
  if (!completePackage || campaign.term_weeks === null) return null;

  const weeks = english
    ? String(campaign.term_weeks)
    : new Intl.NumberFormat("fa-IR", { useGrouping: false }).format(campaign.term_weeks);
  const offer = english
    ? `${weeks} weeks of training + nutrition free`
    : `${weeks} هفته برنامه تمرین + تغذیه رایگان`;
  const content = (
    <>
      <span className="signup-campaign-banner__gift" aria-hidden="true">
        <svg viewBox="0 0 24 24" focusable="false">
          <path d="M4 10h16v10H4zM3 7h18v3H3zM12 7v13M12 7H8.8a2.3 2.3 0 1 1 2.1-3.2L12 7Zm0 0h3.2a2.3 2.3 0 1 0-2.1-3.2L12 7Z" />
        </svg>
      </span>
      <strong>{offer}</strong>
    </>
  );

  if (surface === "landing") {
    return (
      <Link
        className="signup-campaign-banner signup-campaign-banner--landing"
        to="/get-started"
        aria-label={offer}
        data-testid="signup-campaign-banner"
      >
        {content}
      </Link>
    );
  }

  return (
    <aside className="signup-campaign-banner signup-campaign-banner--register" data-testid="signup-campaign-banner">
      {content}
    </aside>
  );
}
