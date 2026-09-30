import { localIsoDate } from "@fitician/core/local-date";
import { useEffect, useState } from "react";

export function useLocalDate(): string {
  const [date, setDate] = useState(localIsoDate);
  useEffect(() => {
    let timer: number | undefined;
    const refresh = () => {
      window.clearTimeout(timer);
      setDate(localIsoDate());
      const now = new Date();
      const midnight = new Date(now);
      midnight.setHours(24, 0, 0, 0);
      timer = window.setTimeout(refresh, Math.min(30_000, midnight.getTime() - now.getTime()));
    };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    refresh();
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, []);
  return date;
}
