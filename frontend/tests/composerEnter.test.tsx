import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { FormEvent, useState } from "react";
import { handleComposerEnterKeyDown } from "../lib/composerEnter";

function ChatStub({ canSubmit }: { canSubmit: boolean }) {
  const [sent, setSent] = useState(false);
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setSent(true);
  };
  return (
    <form onSubmit={onSubmit}>
      <textarea
        data-testid="ta"
        defaultValue="hi"
        onKeyDown={(e) => handleComposerEnterKeyDown(e, canSubmit)}
      />
      <button type="submit">שלח</button>
      {sent ? <p>נשלח</p> : null}
    </form>
  );
}

describe("handleComposerEnterKeyDown", () => {
  afterEach(() => cleanup());

  test("Enter submits parent form when canSubmit", () => {
    render(<ChatStub canSubmit />);
    const ta = screen.getByTestId("ta");
    fireEvent.keyDown(ta, { key: "Enter", shiftKey: false });
    expect(screen.getByText("נשלח")).toBeTruthy();
  });

  test("Enter does not submit when cannot", () => {
    render(<ChatStub canSubmit={false} />);
    const ta = screen.getByTestId("ta");
    const preventDefault = vi.fn();
    fireEvent.keyDown(ta, { key: "Enter", shiftKey: false, preventDefault });
    expect(screen.queryByText("נשלח")).toBeNull();
  });

  test("Shift+Enter does not submit", () => {
    render(<ChatStub canSubmit />);
    const ta = screen.getByTestId("ta");
    fireEvent.keyDown(ta, { key: "Enter", shiftKey: true });
    expect(screen.queryByText("נשלח")).toBeNull();
  });
});
