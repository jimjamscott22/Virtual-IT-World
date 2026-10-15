// Browser behaviour for the workbench. No framework: the server renders every
// view, HTMX swaps partials, and this file only presents what the SSE tick
// reports and wires the few controls that need script.
//
// The simulated world.clock advances one minute per real second server-side
// (routes/events.py) and is pushed here over SSE. Nothing in this file keeps
// its own clock — a reconnecting tab picks up the server's state on the next
// message rather than resuming a countdown of its own.
(() => {
  "use strict";

  function updateShift(payload) {
    const remaining = document.getElementById("shift-remaining");
    if (remaining) {
      remaining.textContent = payload.shift_remaining;
    }
    const rail = document.getElementById("shift-rail");
    if (rail && typeof payload.shift_progress === "number") {
      rail.style.setProperty("--shift-progress", `${payload.shift_progress}%`);
    }
    const track = document.getElementById("shift-track");
    if (track && typeof payload.shift_progress === "number") {
      track.setAttribute("aria-valuenow", String(payload.shift_progress));
    }
    const banner = document.getElementById("shift-banner");
    if (banner) {
      banner.hidden = !payload.shift_over;
    }
  }

  function updateDegraded(payload) {
    const banner = document.getElementById("degraded-banner");
    if (banner) {
      banner.dataset.degraded = payload.degraded ? "true" : "false";
      banner.hidden = !payload.degraded;
    }
  }

  // Each tick updates the per-ticket SLA countdowns in place.
  function updateSlas(activeTickets) {
    for (const t of activeTickets) {
      const el = document.getElementById(`sla-${t.id}`);
      if (el) {
        el.textContent = t.overdue
          ? `${-t.remaining} min overdue`
          : `SLA in ${t.remaining} min`;
      }
    }
  }

  // Filled in by the workbench task: narrows the command list to the
  // selected tool without changing the submitted tool/command/args fields.
  function initializeToolPicker(root = document) {
    return root;
  }

  // Filled in by the responsive task: phone-width queue/detail switching.
  function initializeMasterDetail() {}

  function connect() {
    if (!window.EventSource) {
      return null;
    }
    const source = new EventSource("/events");
    source.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      updateSlas(payload.active);
      updateShift(payload);
      updateDegraded(payload);
      // A non-empty "arrivals" list fires a full queue refresh instead of
      // trying to splice in a new row.
      if (payload.arrivals.length > 0 && window.htmx && document.getElementById("queue")) {
        window.htmx.trigger("#queue", "refresh");
      }
    };
    return source;
  }

  window.VITSC = {
    updateShift,
    updateDegraded,
    updateSlas,
    initializeToolPicker,
    initializeMasterDetail,
    source: null,
  };

  initializeToolPicker();
  initializeMasterDetail();
  window.VITSC.source = connect();
})();
