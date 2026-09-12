"use client";

import { useEffect, useRef } from "react";

export function Modal({
  children,
  titleId,
  onClose,
  drawer = false,
  busy = false,
}: {
  children: React.ReactNode;
  titleId: string;
  onClose: () => void;
  drawer?: boolean;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    const previous =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    const overflow = document.body.style.overflow;
    dialog?.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      dialog?.close();
      document.body.style.overflow = overflow;
      if (previous?.isConnected) previous.focus();
      else document.getElementById("main-content")?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={drawer ? "detail-drawer" : "modal"}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget && !busy) onClose();
      }}
    >
      <div className="dialog-content">{children}</div>
    </dialog>
  );
}
