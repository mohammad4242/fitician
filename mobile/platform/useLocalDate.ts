import { localIsoDate } from "@fitician/core/local-date";
import { useEffect, useState } from "react";
import { AppState } from "react-native";

export function useLocalDate(): string {
  const [date, setDate] = useState(localIsoDate);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = () => {
      clearTimeout(timer);
      setDate(localIsoDate());
      const now = new Date();
      const midnight = new Date(now);
      midnight.setHours(24, 0, 0, 0);
      timer = setTimeout(refresh, Math.min(30_000, midnight.getTime() - now.getTime()));
    };
    const subscription = AppState.addEventListener("change", state => {
      if (state === "active") refresh();
    });
    refresh();
    return () => { clearTimeout(timer); subscription.remove(); };
  }, []);
  return date;
}
