import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import {
  createProgressApi,
  progressCopy,
  progressPresentationCopy,
  progressTabs,
  progressTabLabel,
  resolvedIanaTimeZone,
  type ProgressOverview,
  type ProgressPreset,
  type ProgressTab,
} from "@fitician/core";
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { Button } from "../ui/components/Button";
import { Card } from "../ui/components/Card";
import { Screen } from "../ui/layout";
import { getTextDirectionStyle } from "../ui/rtl";
import { fiticianTokens as t } from "../ui/tokens";
import { useMemberFeatureLanguage } from "../ui/useMemberFeatureLanguage";
import { ProgressOverview as Overview } from "./ProgressOverview";
import Details from "./ProgressDetails";
// Metro bundles native modules together; defer evaluation and history requests until selection.
const AnalysisDetails = lazy(async () => ({
  default: (
    require("../bodyAnalysis/BodyAnalysisHistoryScreen") as typeof import("../bodyAnalysis/BodyAnalysisHistoryScreen")
  ).BodyAnalysisHistoryScreen,
}));
export function ProgressScreen() {
  const auth = useMobileAuth();
  return <ProgressContent key={auth.user?.id} />;
}
function ProgressContent() {
  const auth = useMobileAuth(),
    api = useMemo(() => createProgressApi(auth.request), [auth.request]),
    [language, changeLanguage] = useMemberFeatureLanguage(),
    c = progressCopy[language],
    p = progressPresentationCopy[language],
    direction = language === "fa" ? "rtl" : "ltr",
    text = {
      ...getTextDirectionStyle(direction),
      fontFamily:
        language === "fa"
          ? t.typography.fontFamily.bodyPersian
          : t.typography.fontFamily.bodyEnglish,
    },
    identity = auth.user?.id;
  const [preset, setPreset] = useState<ProgressPreset>("week"),
    [tab, setTab] = useState<ProgressTab>("overview"),
    [data, setData] = useState<ProgressOverview | null>(null),
    [error, setError] = useState(false);
  const epoch = useRef(0);
  const load = useCallback(async () => {
    const current = ++epoch.current;
    setData(null);
    setError(false);
    if (!identity) return;
    try {
      const next = await api.overview(preset, resolvedIanaTimeZone());
      if (epoch.current === current) setData(next);
    } catch {
      if (epoch.current === current) setError(true);
    }
  }, [api, preset, identity]);
  useEffect(() => {
    void load();
    return () => {
      epoch.current++;
    };
  }, [load]);
  return (
    <Screen
      contentWidth="reading"
      keyboardAware
      contentContainerStyle={{ direction }}
    >
      <View style={styles.stack}>
        <View style={styles.header}>
          <Text accessibilityRole="header" style={[styles.title, text]}>
            {c.title}
          </Text>
          <Button
            variant="ghost"
            label={language === "fa" ? "English" : "فارسی"}
            onPress={() => changeLanguage(language === "fa" ? "en" : "fa")}
          />
        </View>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.tabs}
          contentContainerStyle={[styles.tabRow, { direction }]}
        >
          {progressTabs(data).map(({ id, disabled }) => (
            <Pressable
              key={id}
              accessibilityRole="tab"
              accessibilityLabel={progressTabLabel(id, language)}
              accessibilityState={{ selected: tab === id, disabled }}
              disabled={disabled}
              onPress={() => setTab(id)}
              style={[
                styles.tab,
                tab === id && styles.activeTab,
                disabled && styles.disabled,
              ]}
            >
              <Text
                style={[styles.tabText, text, tab === id && styles.activeText]}
              >
                {progressTabLabel(id, language)}
              </Text>
            </Pressable>
          ))}
        </ScrollView>
        <Text style={[styles.context, text]}>
          {data?.context.week_number != null
            ? `${c.programWeek} ${new Intl.NumberFormat(language).format(data.context.week_number)} · ${c.program}`
            : c[preset]}
        </Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          accessibilityLabel={p.period}
          contentContainerStyle={[styles.ranges, { direction }]}
        >
          {(["week", "four_weeks", "current_program"] as const).map((range) => (
            <Pressable
              key={range}
              accessibilityRole="button"
              accessibilityLabel={c[range]}
              accessibilityState={{ selected: preset === range }}
              onPress={() => setPreset(range)}
              style={[styles.range, preset === range && styles.activeRange]}
            >
              <Text
                style={[
                  styles.rangeText,
                  text,
                  preset === range && styles.activeText,
                ]}
              >
                {c[range]}
              </Text>
            </Pressable>
          ))}
        </ScrollView>
        {error ? (
          <Card direction={direction}>
            <Text accessibilityRole="alert" style={[styles.context, text]}>
              {c.error}
            </Text>
            <Button label={c.retry} onPress={() => void load()} />
          </Card>
        ) : !data ? (
          <ActivityIndicator
            accessibilityLabel={c.loading}
            color={t.colors.aqua}
          />
        ) : (
          <>
            {data.context.range_clipped && (
              <Text style={[styles.context, text]}>{c.clipped}</Text>
            )}
            {tab === "overview" ? (
              <Overview data={data} language={language} onSelect={setTab} />
            ) : (
              <Suspense
                fallback={
                  <ActivityIndicator
                    accessibilityLabel={c.loading}
                    color={t.colors.aqua}
                  />
                }
              >
                {tab === "analysis" ? (
                  <AnalysisDetails embedded tabRoot />
                ) : (
                  <Details
                    key={preset}
                    tab={tab}
                    data={data}
                    language={language}
                    api={api}
                    onSaved={load}
                  />
                )}
              </Suspense>
            )}
          </>
        )}
      </View>
    </Screen>
  );
}
const styles = StyleSheet.create({
  stack: { gap: 12, paddingBottom: 16 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  title: {
    color: t.colors.ink,
    fontSize: 25,
    fontWeight: "800",
    fontFamily: t.typography.fontFamily.bodyPersian,
  },
  tabs: { borderBottomWidth: 1, borderBottomColor: t.colors.line },
  tabRow: { flexDirection: "row", gap: 22 },
  tab: {
    minWidth: 48,
    minHeight: 48,
    justifyContent: "center",
    borderBottomWidth: 3,
    borderBottomColor: "transparent",
    paddingHorizontal: 2,
  },
  activeTab: { borderBottomColor: t.colors.aqua },
  tabText: {
    fontSize: 14,
    color: t.colors.muted,
    fontFamily: t.typography.fontFamily.bodyPersian,
  },
  activeText: { color: t.colors.aqua, fontWeight: "700" },
  disabled: { opacity: 0.35 },
  context: {
    color: t.colors.muted,
    fontSize: 12,
    fontFamily: t.typography.fontFamily.bodyPersian,
  },
  ranges: { flexDirection: "row", gap: 4 },
  range: {
    minHeight: 48,
    paddingHorizontal: 14,
    borderRadius: 12,
    justifyContent: "center",
  },
  activeRange: { backgroundColor: t.colors.surfaceRaised },
  rangeText: {
    color: t.colors.muted,
    fontSize: 12,
    fontFamily: t.typography.fontFamily.bodyPersian,
  },
});
