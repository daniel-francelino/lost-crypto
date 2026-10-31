import { useEffect, useState } from "react";
import { nowMs } from "@/lib/shared/dates";

const ONE_SECOND = 1000;

export const useNow = (intervalMs: number = ONE_SECOND): number => {
  const [now, setNow] = useState(nowMs);

  useEffect(() => {
    const timer = setInterval(() => setNow(nowMs()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);

  return now;
};
