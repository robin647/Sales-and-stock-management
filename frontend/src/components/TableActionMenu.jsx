import { useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import "./table-action-menu.css";

export default function TableActionMenu({ children }) {
  const [open, setOpen] = useState(false);
  const trigger = useRef(null);
  const popup = useRef(null);
  const id = useId();

  useLayoutEffect(() => {
    if (!open) return;
    const panel = popup.current;
    const rect = trigger.current.getBoundingClientRect();
    const gap = 8;
    const height = Math.min(panel.scrollHeight, window.innerHeight - 2 * gap);
    const top = rect.bottom + gap + height <= window.innerHeight
      ? rect.bottom + gap : Math.max(gap, rect.top - height - gap);
    panel.style.top = `${top}px`;
    panel.style.left = `${Math.max(gap, Math.min(rect.right - panel.offsetWidth, window.innerWidth - panel.offsetWidth - gap))}px`;
    const items = () => [...panel.querySelectorAll("button:not(:disabled), a[href]")];
    panel.querySelectorAll("button, a[href]").forEach(item => {
      item.setAttribute("role", "menuitem");
      if (item.tagName === "BUTTON") item.setAttribute("type", "button");
    });
    items()[0]?.focus();
    const outside = event => {
      if (!panel.contains(event.target) && !trigger.current?.contains(event.target)) setOpen(false);
    };
    const keydown = event => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        setOpen(false);
        trigger.current?.focus();
      } else if (event.key === "Tab") {
        setOpen(false);
        trigger.current?.focus();
      } else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
        event.preventDefault();
        const options = items();
        const current = options.indexOf(document.activeElement);
        const next = event.key === "Home" ? 0 : event.key === "End" ? options.length - 1
          : (current + (event.key === "ArrowDown" ? 1 : -1) + options.length) % options.length;
        options[next]?.focus();
      }
    };
    const close = event => { if (!panel.contains(event.target)) setOpen(false); };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", keydown, true);
    document.addEventListener("focusin", outside);
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", keydown, true);
      document.removeEventListener("focusin", outside);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
    };
  }, [open]);

  return <>
    <button ref={trigger} type="button" className="table-action-trigger" aria-label="Row actions"
      aria-haspopup="menu" aria-expanded={open} aria-controls={open ? id : undefined}
      onClick={() => setOpen(value => !value)}
      onKeyDown={event => { if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); setOpen(true); } }}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="5" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="12" cy="19" r="2" /></svg>
    </button>
    {open && createPortal(<div ref={popup} id={id} role="menu" aria-label="Row actions" className="table-action-popup"
      onClick={event => {
        const item = event.target.closest("button, a[href]");
        if (item && !item.disabled) setOpen(false);
      }}>{children}</div>, document.body)}
  </>;
}
