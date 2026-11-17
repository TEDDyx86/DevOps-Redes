const KEY = "workbyte-sidebar-collapsed";

function storage(): Pick<Storage, "getItem" | "setItem" | "removeItem"> | null {
  try {
    if (typeof window === "undefined" || !window.localStorage) return null;
    return window.localStorage;
  } catch {
    return null;
  }
}

export function readSidebarPreference(): boolean {
  return storage()?.getItem(KEY) === "1";
}

export function saveSidebarPreference(collapsed: boolean) {
  const store = storage();
  if (!store) return;
  if (collapsed) store.setItem(KEY, "1");
  else store.removeItem(KEY);
}
