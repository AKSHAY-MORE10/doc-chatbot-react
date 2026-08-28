import { useEffect, useState } from "react";

function readStorage(storage, key, fallback) {
  try {
    const raw = storage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function useStorageState(storage, key, fallback) {
  const [value, setValue] = useState(() => readStorage(storage, key, fallback));

  useEffect(() => {
    try {
      storage.setItem(key, JSON.stringify(value));
    } catch {
      // storage full or unavailable — non-fatal, chat still works in-memory
    }
  }, [key, value, storage]);

  return [value, setValue];
}

export function useLocalStorageState(key, fallback) {
  return useStorageState(window.localStorage, key, fallback);
}

export function useSessionStorageState(key, fallback) {
  return useStorageState(window.sessionStorage, key, fallback);
}
