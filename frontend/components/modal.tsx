"use client";

import { useEffect, useRef, useState } from "react";

function isOutsideDialog(event: React.MouseEvent<HTMLDialogElement>) {
  const bounds = event.currentTarget.getBoundingClientRect();
  return (
    event.target === event.currentTarget &&
    (event.clientX < bounds.left ||
      event.clientX >= bounds.right ||
      event.clientY < bounds.top ||
      event.clientY >= bounds.bottom)
  );
}

export function Modal({
  children,
  titleId,
  descriptionId,
  onClose,
  drawer = false,
  closing = false,
  onExitComplete,
  busy = false,
}: {
  children: React.ReactNode;
  titleId: string;
  descriptionId?: string;
  onClose: () => void;
  drawer?: boolean;
  closing?: boolean;
  onExitComplete?: () => void;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const pressedOutside = useRef(false);
  const exitCompleteRef = useRef(onExitComplete);
  const [entered, setEntered] = useState(false);
  useEffect(() => {
    exitCompleteRef.current = onExitComplete;
  }, [onExitComplete]);
  useEffect(() => {
    const dialog = ref.current;
    const previous =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    const overflow = document.body.style.overflow;
    dialog?.showModal();
    dialog?.querySelector<HTMLElement>("[data-initial-focus]")?.focus();
    // A preview leaves the feed scrollable; forms still lock the page.
    if (!drawer) document.body.style.overflow = "hidden";
    // Paint the native dialog in its faded, offset position before transitioning in.
    // This also avoids relying on display/top-layer animation support in Safari.
    let frame = 0;
    if (drawer) {
      frame = requestAnimationFrame(() => {
        frame = requestAnimationFrame(() => setEntered(true));
      });
    }
    return () => {
      cancelAnimationFrame(frame);
      dialog?.close();
      if (!drawer) document.body.style.overflow = overflow;
      if (previous?.isConnected) previous.focus({ preventScroll: drawer });
      else document.getElementById("main-content")?.focus({ preventScroll: drawer });
    };
  }, [drawer]);
  useEffect(() => {
    if (!drawer || !closing) return;
    const dialog = ref.current;
    if (!dialog) return;
    const duration = Math.max(
      ...getComputedStyle(dialog).transitionDuration
        .split(",")
        .map((value) => parseFloat(value) * 1000),
    );
    // A transition can be absent (reduced motion or a very early close) or
    // cancelled. Always finish dismissal and restore focus in those cases too.
    const timeout = setTimeout(
      () => exitCompleteRef.current?.(),
      entered && duration > 0 ? duration + 50 : 0,
    );
    return () => clearTimeout(timeout);
  }, [drawer, closing, entered]);
  return (
    <dialog
      ref={ref}
      className={
        drawer ? `detail-drawer${closing ? " is-closing" : ""}` : "modal"
      }
      data-visible={drawer && entered && !closing}
      onTransitionEnd={(event) => {
        if (
          closing &&
          event.target === event.currentTarget &&
          event.propertyName === "opacity" &&
          Number(getComputedStyle(event.currentTarget).opacity) <= 0.001
        ) {
          onExitComplete?.();
        }
      }}
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      tabIndex={-1}
      onKeyDown={(event) => {
        if (event.nativeEvent.isComposing) return;
        if (event.key === "Escape") {
          // Search inputs otherwise consume Escape to clear their value before
          // the native dialog receives its cancel event.
          event.preventDefault();
          event.stopPropagation();
          if (!busy) onClose();
          return;
        }
        if (
          event.key !== "Tab" ||
          event.ctrlKey ||
          event.altKey ||
          event.metaKey
        )
          return;
        const dialog = event.currentTarget;
        const controls = Array.from(
          dialog.querySelectorAll<HTMLElement>(
            'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), summary, [tabindex]:not([tabindex="-1"])',
          ),
        ).filter(
          (element) =>
            element.getClientRects().length > 0 &&
            getComputedStyle(element).visibility !== "hidden",
        );
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (!first) {
          event.preventDefault();
          dialog.focus();
        } else if (
          event.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === dialog)
        ) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      onPointerDown={(event) => {
        pressedOutside.current = isOutsideDialog(event);
      }}
      onPointerCancel={() => {
        pressedOutside.current = false;
      }}
      onClick={(event) => {
        // Blank space inside a native dialog also targets the dialog itself.
        // Dismiss only a press and release outside, not an internal click or drag.
        const dismiss = pressedOutside.current && isOutsideDialog(event);
        pressedOutside.current = false;
        if (dismiss && !busy) onClose();
      }}
    >
      <div className="dialog-content">{children}</div>
    </dialog>
  );
}
