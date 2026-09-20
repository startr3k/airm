import { createContext, useContext } from "react";

/** One sheet for the whole app: chips call `open(itemId)` rather than each mounting a
 *  dialog of its own. Kept apart from the provider so that file exports components only. */
export const SourceContext = createContext<(itemId: string) => void>(() => {});

export function useSource() {
  return useContext(SourceContext);
}
