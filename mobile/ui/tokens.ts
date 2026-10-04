export type FiticianTokens = {
  readonly colors: {
    readonly onAccent: string;
    readonly onDanger: string;
    readonly accentInk: string;
    readonly mediaCanvas: string;
    readonly mediaInk: string;
    readonly catalogueSurface: string;
    readonly catalogueChip: string;
    readonly foodCard: string;
    readonly scienceSurface: string;
    readonly supervisionSurface: string;
    readonly experienceTabs: string;
    readonly emptyHero: string;
    readonly emptyAtmosphere: string;
    readonly successStrong: string;
    readonly warningBright: string;
    readonly dangerSoft: string;
    readonly dangerMuted: string;
    readonly warningFill: string;
    readonly successFill: string;
    readonly coralFill: string;
    readonly canvas: string;
    readonly petrol: string;
    readonly teal: string;
    readonly surface: string;
    readonly surfaceSubtle: string;
    readonly surfaceRaised: string;
    readonly surfaceTranslucent: string;
    readonly hero: string;
    readonly mediaOverlay: string;
    readonly scrim: string;
    readonly surfaceInteractive: string;
    readonly infoSurface: string;
    readonly warningSurface: string;
    readonly successSurface: string;
    readonly dangerSurface: string;
    readonly aqua: string;
    readonly blue: string;
    readonly coral: string;
    readonly amber: string;
    readonly success: string;
    readonly danger: string;
    readonly mist: string;
    readonly ink: string;
    readonly muted: string;
    readonly line: string;
    readonly lineStrong: string;
    readonly aquaAtmosphere: string;
    readonly progressTrack: string;
    readonly surfaceHighlight: string;
  };
  readonly spacing: Readonly<Record<1 | 2 | 3 | 4 | 5 | 6 | 7 | 8, number>>;
  readonly radii: {
    readonly small: number;
    readonly medium: number;
    readonly large: number;
    readonly extraLarge: number;
    readonly card: number;
    readonly pill: number;
  };
  readonly typography: {
    readonly fontFamily: {
      readonly bodyEnglish: string;
      readonly bodyPersian: string;
      readonly displayEnglish: string;
      readonly displayPersian: string;
    };
    readonly fontSize: Readonly<Record<"xs" | "sm" | "body" | "lg" | "h3" | "h2" | "h1" | "display" | "metric" | "compact", number>>;
    readonly lineHeight: Readonly<Record<"tight" | "body" | "loose", number>>;
    readonly fontWeight: Readonly<Record<"regular" | "medium" | "bold" | "extraBold", "400" | "500" | "700" | "800">>;
  };
  readonly iconSize: Readonly<Record<"sm" | "md" | "lg" | "xl", number>>;
  readonly shadows: {
    readonly card: NativeShadowToken;
    readonly soft: NativeShadowToken;
    readonly focus: NativeShadowToken;
    readonly glow: NativeShadowToken;
  };
  readonly motion: {
    readonly fastMs: number;
    readonly mediumMs: number;
    readonly easing: "easeOutCubic";
    readonly pressedScale: number;
  };
  readonly layout: {
    readonly screenPadding: number;
    readonly tabletPadding: number;
    readonly contentMaxWidth: number;
    readonly readingMaxWidth: number;
    readonly minimumTouchTarget: number;
  };
};

export type NativeShadowToken = {
  readonly color: string;
  readonly offset: { readonly width: number; readonly height: number };
  readonly opacity: number;
  readonly radius: number;
  readonly elevation: number;
};

export const darkColors = {
    onAccent: "#020607",
    onDanger: "#020607",
    accentInk: "#50dfce",
    mediaCanvas: "#020607",
    mediaInk: "#e8f4f1",
    amber: "#f2b85b",
    aqua: "#50dfce",
    blue: "#3b82f6",
    catalogueSurface: "rgba(10,31,30,0.75)",
    catalogueChip: "rgba(10,31,30,0.65)",
    foodCard: "#0a1b1a",
    scienceSurface: "rgba(9,54,51,0.52)",
    supervisionSurface: "rgba(9,54,51,0.45)",
    experienceTabs: "rgba(8,22,27,0.85)",
    emptyHero: "rgba(2,9,10,0.84)",
    emptyAtmosphere: "rgba(2,9,10,0.22)",
    successStrong: "#10b981",
    warningBright: "#ffd798",
    dangerSoft: "#fca5a5",
    dangerMuted: "#fecaca",
    warningFill: "#f2b85b",
    successFill: "#66c89f",
    coralFill: "#f67859",
    canvas: "#020607",
    coral: "#f67859",
    danger: "#f67859",
    ink: "#e8f4f1",
    line: "rgba(232,244,241,0.12)",
    lineStrong: "rgba(80,223,206,0.28)",
    aquaAtmosphere: "rgba(80,223,206,0.10)",
    progressTrack: "rgba(232,244,241,0.10)",
    surfaceHighlight: "rgba(255,255,255,0.05)",
    mist: "#e8f4f1",
    muted: "#94aba5",
    petrol: "#091817",
    success: "#66c89f",
    surface: "#081211",
    surfaceInteractive: "rgba(80,223,206,0.07)",
    surfaceRaised: "#101e1c",
    surfaceSubtle: "#050b0c",
    surfaceTranslucent: "rgba(16,30,28,0.78)",
    hero: "#102522",
    mediaOverlay: "rgba(2,6,7,0.72)",
    scrim: "rgba(2,6,7,0.56)",
    infoSurface: "rgba(80,223,206,0.08)",
    warningSurface: "rgba(242,184,91,0.12)",
    successSurface: "rgba(102,200,159,0.12)",
    dangerSurface: "rgba(246,120,89,0.12)",
    teal: "#0e201e",
} as const satisfies FiticianTokens["colors"];

export const fiticianTokens = {
  colors: darkColors,
  layout: {
    contentMaxWidth: 1_312,
    minimumTouchTarget: 48,
    readingMaxWidth: 1_088,
    screenPadding: 16,
    tabletPadding: 32,
  },
  motion: {
    easing: "easeOutCubic",
    fastMs: 160,
    mediumMs: 260,
    pressedScale: 0.985,
  },
  radii: {
    card: 18,
    extraLarge: 24,
    large: 18,
    medium: 14,
    pill: 999,
    small: 10,
  },
  shadows: {
    card: {
      color: "#000000",
      elevation: 3,
      offset: { height: 2, width: 0 },
      opacity: 0.25,
      radius: 10,
    },
    focus: {
      color: "#000000",
      elevation: 4,
      offset: { height: 4, width: 0 },
      opacity: 0.24,
      radius: 18,
    },
    glow: {
      color: "#50dfce",
      elevation: 4,
      offset: { height: 2, width: 0 },
      opacity: 0.24,
      radius: 9,
    },
    soft: {
      color: "#000000",
      elevation: 2,
      offset: { height: 2, width: 0 },
      opacity: 0.22,
      radius: 8,
    },
  },
  spacing: {
    1: 4,
    2: 8,
    3: 12,
    4: 16,
    5: 24,
    6: 32,
    7: 48,
    8: 72,
  },
  iconSize: {
    sm: 18,
    md: 22,
    lg: 28,
    xl: 36,
  },
  typography: {
    fontFamily: {
      bodyEnglish: "Sora",
      bodyPersian: "Vazirmatn",
      displayEnglish: "Sora",
      displayPersian: "Lalezar",
    },
    fontSize: {
      body: 16,
      compact: 13,
      display: 38,
      h1: 32,
      h2: 24,
      h3: 20,
      lg: 18,
      metric: 28,
      sm: 14,
      xs: 12,
    },
    fontWeight: {
      bold: "700",
      extraBold: "800",
      medium: "500",
      regular: "400",
    },
    lineHeight: {
      body: 1.5,
      loose: 1.85,
      tight: 1.15,
    },
  },
} as const satisfies FiticianTokens;

export type FiticianTheme = "dark" | "light";
export const lightColors: FiticianTokens["colors"] = {
  ...darkColors,
  catalogueSurface: "#ffffff",
  catalogueChip: "#f0f6f3",
  foodCard: "#ffffff",
  scienceSurface: "#e2f7f1",
  supervisionSurface: "#e2f7f1",
  experienceTabs: "#f0f6f3",
  emptyHero: "#eaf4f0",
  emptyAtmosphere: "rgba(80,223,206,0.12)",
  successStrong: "#23734f",
  warningBright: "#8b5a10",
  dangerSoft: "#b74025",
  dangerMuted: "#b74025",
  canvas: "#f5faf8",
  petrol: "#eaf4f0",
  teal: "#e2efea",
  surface: "#ffffff",
  surfaceSubtle: "#f0f6f3",
  surfaceRaised: "#edf5f1",
  surfaceTranslucent: "rgba(255,255,255,0.96)",
  surfaceInteractive: "#e2f7f1",
  hero: "#e2f7f1",
  ink: "#102422",
  mist: "#102422",
  muted: "#526b65",
  accentInk: "#087568",
  blue: "#245ec1",
  coral: "#b74025",
  danger: "#b74025",
  amber: "#8b5a10",
  success: "#23734f",
  onDanger: "#ffffff",
  line: "rgba(16,36,34,0.13)",
  lineStrong: "rgba(8,117,104,0.34)",
  aquaAtmosphere: "rgba(80,223,206,0.16)",
  progressTrack: "rgba(16,36,34,0.10)",
  surfaceHighlight: "rgba(16,36,34,0.04)",
  infoSurface: "#e2f7f1",
  warningSurface: "#fff4df",
  successSurface: "#e8f5ec",
  dangerSurface: "#fff0ea",
};
const lightTokens: FiticianTokens = {
  ...fiticianTokens,
  colors: lightColors,
  shadows: {
    card: { ...fiticianTokens.shadows.card, color: "#102422", opacity: 0.06, elevation: 2 },
    soft: { ...fiticianTokens.shadows.soft, color: "#102422", opacity: 0.06, elevation: 1 },
    focus: { ...fiticianTokens.shadows.focus, color: "#102422", opacity: 0.09, elevation: 3 },
    glow: { ...fiticianTokens.shadows.glow, color: "#087568", opacity: 0.12, elevation: 2 },
  },
};
export function getThemeTokens(theme: FiticianTheme): FiticianTokens {
  return theme === "light" ? lightTokens : fiticianTokens;
}
