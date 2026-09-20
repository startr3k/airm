/** The Assess form's shape and its empty state.
 *
 * These live apart from `InputPanel` so that file exports components only -- React Fast
 * Refresh cannot swap a module that mixes components with other values.
 */

export const PATTERNS = [
  { value: "build", label: "Build" },
  { value: "onboard", label: "Onboard" },
  { value: "onboard_with_customisation", label: "Onboard + customise" },
] as const;

export type DeploymentPattern = (typeof PATTERNS)[number]["value"];

export interface AssessFormState {
  description: string;
  deploymentPattern: DeploymentPattern | null;
  isAgentic: boolean;
  toolsAccessible: string[];
  customerFacing: boolean;
  model: string;
}

export const INITIAL_FORM: AssessFormState = {
  description: "",
  deploymentPattern: null,
  isAgentic: false,
  toolsAccessible: [],
  customerFacing: false,
  model: "claude-sonnet-5",
};
