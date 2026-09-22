import fiticianLogo from "../assets/branding/fitician-logo-horizontal.webp";

type BrandLogoProps = {
  className?: string;
  testId?: string;
};

export function BrandLogo({ className, testId }: BrandLogoProps) {
  const classes = ["fitician-brand-logo", className].filter(Boolean).join(" ");

  return (
    <img
      src={fiticianLogo}
      alt=""
      width="1500"
      height="500"
      className={classes}
      data-testid={testId}
    />
  );
}
