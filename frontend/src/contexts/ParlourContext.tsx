import { createContext, useContext, useState, type ReactNode } from "react";

const STORAGE_KEY = "fire_tracker_selected_parlour";

interface ParlourSelection {
  parlourId: string;
  role: "owner" | "data_entry";
}

interface ParlourContextType {
  selectedParlourId: string | null;
  role: "owner" | "data_entry" | null;
  setSelectedParlour: (parlourId: string | null, role?: "owner" | "data_entry") => void;
}

const ParlourContext = createContext<ParlourContextType | null>(null);

function readStored(): ParlourSelection | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ParlourSelection;
    if (!parsed.parlourId) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function ParlourProvider({ children }: { children: ReactNode }) {
  const [selection, setSelection] = useState<ParlourSelection | null>(readStored);

  const setSelectedParlour = (
    parlourId: string | null,
    role?: "owner" | "data_entry"
  ) => {
    if (!parlourId) {
      localStorage.removeItem(STORAGE_KEY);
      setSelection(null);
      return;
    }
    const next = { parlourId, role: role ?? "data_entry" };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setSelection(next);
  };

  return (
    <ParlourContext.Provider
      value={{
        selectedParlourId: selection?.parlourId ?? null,
        role: selection?.role ?? null,
        setSelectedParlour,
      }}
    >
      {children}
    </ParlourContext.Provider>
  );
}

export function useParlour(): ParlourContextType {
  const ctx = useContext(ParlourContext);
  if (!ctx) throw new Error("useParlour must be used within a ParlourProvider");
  return ctx;
}
