import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const STORAGE_KEY = "secure-knowledge.selected-organization";

export interface SelectedOrganization {
  id: string;
  name: string;
}

interface SelectedOrganizationContextValue {
  organization: SelectedOrganization | null;
  selectOrganization: (organization: SelectedOrganization) => void;
  clearOrganization: () => void;
}

const SelectedOrganizationContext =
  createContext<SelectedOrganizationContextValue | null>(null);

function readStoredOrganization(): SelectedOrganization | null {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (!stored) {
    return null;
  }

  try {
    const value: unknown = JSON.parse(stored);
    if (
      typeof value === "object" &&
      value !== null &&
      "id" in value &&
      "name" in value &&
      typeof value.id === "string" &&
      typeof value.name === "string"
    ) {
      return { id: value.id, name: value.name };
    }
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
  }

  return null;
}

export function SelectedOrganizationProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [organization, setOrganization] =
    useState<SelectedOrganization | null>(readStoredOrganization);

  const selectOrganization = useCallback(
    (nextOrganization: SelectedOrganization) => {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(nextOrganization),
      );
      setOrganization(nextOrganization);
    },
    [],
  );

  const clearOrganization = useCallback(() => {
    window.localStorage.removeItem(STORAGE_KEY);
    setOrganization(null);
  }, []);

  const value = useMemo(
    () => ({ organization, selectOrganization, clearOrganization }),
    [organization, selectOrganization, clearOrganization],
  );

  return (
    <SelectedOrganizationContext.Provider value={value}>
      {children}
    </SelectedOrganizationContext.Provider>
  );
}

export function useSelectedOrganization() {
  const context = useContext(SelectedOrganizationContext);
  if (!context) {
    throw new Error(
      "useSelectedOrganization must be used inside its provider.",
    );
  }
  return context;
}
