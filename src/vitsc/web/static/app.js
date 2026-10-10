(function () {
  "use strict";
  function updateShift(payload) {
    const remaining = document.getElementById("shift-remaining");
    if (remaining) remaining.textContent = payload.shift_remaining;
    const rail = document.querySelector(".shift-rail");
    if (rail) rail.style.setProperty("--shift-progress", `${payload.shift_progress}%`);
    const banner = document.getElementById("shift-banner");
    if (banner) banner.hidden = !payload.shift_over;
  }
  function updateSlas(activeTickets) {
    activeTickets.forEach((ticket) => {
      const element = document.getElementById(`sla-${ticket.id}`);
      if (!element) return;
      element.textContent = ticket.overdue ? `${-ticket.remaining} min overdue` : `Due in ${ticket.remaining} min`;
      const row = element.closest(".ticket-row");
      if (row) row.dataset.overdue = ticket.overdue ? "true" : "false";
    });
  }
  function initializeToolPicker(root = document) {
    root.querySelectorAll("[data-tool-picker]").forEach((toolPicker) => {
      const form = toolPicker.closest("form");
      const commandPicker = form && form.querySelector("[data-command-picker]");
      if (!commandPicker) return;
      const filter = () => {
        let first = null;
        Array.from(commandPicker.options).forEach((option) => {
          const matches = option.dataset.tool === toolPicker.value;
          option.hidden = !matches; option.disabled = !matches;
          if (matches && !first) first = option;
        });
        if (!commandPicker.selectedOptions[0] || commandPicker.selectedOptions[0].disabled) commandPicker.value = first ? first.value : "";
      };
      if (!toolPicker.dataset.filterReady) { toolPicker.addEventListener("change", filter); toolPicker.dataset.filterReady = "true"; }
      filter();
    });
  }
  let selectedTicketId = null;
  function initializeMasterDetail() {
    document.addEventListener("click", (event) => {
      const row = event.target.closest(".ticket-row");
      if (row) selectedTicketId = row.dataset.ticketId;
      if (event.target.closest(".back-to-queue")) {
        document.querySelector(".layout")?.classList.remove("ticket-open");
        document.querySelector(`.ticket-row[data-ticket-id='${selectedTicketId}']`)?.focus();
      }
    });
  }
  document.addEventListener("htmx:afterSwap", (event) => {
    initializeToolPicker(event.target);
    if (event.target.id === "detail" && event.target.querySelector(".case-workspace")) {
      document.querySelector(".layout")?.classList.add("ticket-open");
      event.target.querySelector("#ticket-heading")?.focus();
    }
  });
  document.addEventListener("DOMContentLoaded", () => { initializeToolPicker(); initializeMasterDetail(); });
  if (window.EventSource) {
    const source = new EventSource("/events");
    source.onmessage = (event) => {
      const payload = JSON.parse(event.data); updateShift(payload); updateSlas(payload.active);
      const banner = document.getElementById("degraded-banner");
      if (banner) { banner.dataset.degraded = payload.degraded ? "true" : "false"; banner.hidden = !payload.degraded; }
      if (payload.arrivals.length > 0 && window.htmx) window.htmx.trigger("#queue", "refresh");
    };
  }
  window.VITSC = { updateShift, updateSlas, initializeToolPicker, initializeMasterDetail };
}());
