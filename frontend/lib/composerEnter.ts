import type { KeyboardEvent } from "react";

/**
 * Chat-style composer: Enter submits the parent form; Shift+Enter inserts a newline.
 * Returns true if the event was handled (default prevented).
 */
export function handleComposerEnterKeyDown(e: KeyboardEvent<HTMLTextAreaElement>, canSubmit: boolean): boolean {
  if (e.key !== "Enter" || e.shiftKey) {
    return false;
  }
  if (!canSubmit) {
    return false;
  }
  e.preventDefault();
  const form = e.currentTarget.form;
  if (form) {
    form.requestSubmit();
  }
  return true;
}
