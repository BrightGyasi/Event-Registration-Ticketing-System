(() => {
  "use strict";

  const API_BASE = (window.APP_CONFIG && window.APP_CONFIG.API_BASE) || "";

  const $ = (id) => document.getElementById(id);

  const eventsGrid = $("eventsGrid");
  const eventsState = $("eventsState");
  const eventsStateText = $("eventsStateText");
  const eventsRetry = $("eventsRetry");
  const heroCount = $("heroCount");
  const statusDot = $("statusDot");
  const statusText = $("statusText");

  const lookupForm = $("lookupForm");
  const lookupEmail = $("lookupEmail");
  const ticketsGrid = $("ticketsGrid");
  const ticketsState = $("ticketsState");
  const ticketsStateText = $("ticketsStateText");

  const registerDialog = $("registerDialog");
  const registerForm = $("registerForm");
  const registerStep = $("registerStep");
  const confirmStep = $("confirmStep");
  const dialogEventName = $("dialogEventName");
  const dialogEventMeta = $("dialogEventMeta");
  const regName = $("regName");
  const regEmail = $("regEmail");
  const registerError = $("registerError");
  const registerSubmit = $("registerSubmit");
  const dialogClose = $("dialogClose");
  const dialogCancel = $("dialogCancel");
  const confirmEventName = $("confirmEventName");
  const confirmEventMeta = $("confirmEventMeta");
  const confirmId = $("confirmId");
  const confirmDone = $("confirmDone");

  const toast = $("toast");
  let toastTimer;

  let activeEvent = null;
  let lastRegisteredEmail = "";

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 3200);
  }

  function fmtDate(value) {
    if (!value) return "Date TBD";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }

  async function api(path, options = {}) {
    if (!API_BASE || API_BASE.includes("REPLACE-ME")) {
      throw new Error("CONFIG_MISSING");
    }
    const res = await fetch(API_BASE.replace(/\/?$/, "/") + path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    let body = null;
    try { body = await res.json(); } catch (_) { /* no body */ }
    if (!res.ok) {
      const message = (body && (body.error || body.message)) || `Request failed (${res.status})`;
      const err = new Error(message);
      err.status = res.status;
      throw err;
    }
    return body;
  }

  // ---------------- Events ----------------

  function renderEventsSkeleton() {
    eventsGrid.innerHTML = "";
    for (let i = 0; i < 3; i++) {
      const el = document.createElement("div");
      el.className = "stub-card skeleton";
      el.style.height = "150px";
      eventsGrid.appendChild(el);
    }
  }

  function eventCard(ev) {
    const capacity = Number(ev.capacity ?? 0);
    const registered = Number(ev.registeredCount ?? 0);
    const remaining = Math.max(capacity - registered, 0);
    const full = capacity > 0 && remaining <= 0;
    const pct = capacity > 0 ? Math.min((registered / capacity) * 100, 100) : 0;

    const card = document.createElement("article");
    card.className = "stub-card event-card" + (full ? " is-full" : "");

    card.innerHTML = `
      <div class="stub-main">
        <p class="stub-eyebrow">${fmtDate(ev.eventDate)}</p>
        <p class="stub-title">${escapeHtml(ev.eventName || ev.eventId)}</p>
        <p class="stub-meta">${escapeHtml(ev.location || "Location TBD")}</p>
      </div>
      <div class="stub-notch stub-notch-top"></div>
      <div class="stub-notch stub-notch-bottom"></div>
      <div class="stub-tear"></div>
      <div class="stub-side">
        <p class="stub-code">SEATS</p>
        <p class="stub-seat">${full ? "0" : remaining}</p>
        <p class="stub-seat-label">${full ? "sold out" : "left"}</p>
      </div>
      <div class="event-actions">
        <div class="seats-meter">
          <p class="seats-label">${registered}/${capacity || "?"} reserved</p>
          <div class="seats-bar"><div class="seats-fill${full ? " full" : ""}" style="width:${pct}%"></div></div>
        </div>
        <button class="btn btn-small btn-primary" type="button" ${full ? "disabled" : ""}>
          ${full ? "Full" : "Reserve seat"}
        </button>
      </div>
    `;

    const btn = card.querySelector("button.btn-primary");
    if (!full) {
      btn.addEventListener("click", () => openRegisterDialog(ev));
    }
    return card;
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  async function loadEvents() {
    eventsState.hidden = true;
    eventsRetry.hidden = true;
    renderEventsSkeleton();

    try {
      const data = await api("events");
      const events = data.events || [];
      statusDot.className = "status-dot ok";
      statusText.textContent = "API connected";

      if (events.length === 0) {
        eventsGrid.innerHTML = "";
        eventsState.hidden = false;
        eventsStateText.textContent = "No events open right now — check back soon.";
        heroCount.textContent = "0";
        return;
      }

      eventsGrid.innerHTML = "";
      events.forEach((ev) => eventsGrid.appendChild(eventCard(ev)));
      const openCount = events.filter((ev) => {
        const cap = Number(ev.capacity ?? 0);
        const reg = Number(ev.registeredCount ?? 0);
        return cap === 0 || reg < cap;
      }).length;
      heroCount.textContent = openCount;
    } catch (err) {
      eventsGrid.innerHTML = "";
      statusDot.className = "status-dot error";
      eventsState.hidden = false;
      eventsRetry.hidden = false;

      if (err.message === "CONFIG_MISSING") {
        statusText.textContent = "Not configured";
        eventsStateText.textContent = "This site isn't pointed at an API yet — set API_BASE in config.js.";
        eventsRetry.hidden = true;
      } else {
        statusText.textContent = "API unreachable";
        eventsStateText.textContent = "Couldn't load events. Make sure the API is reachable, then try again.";
      }
    }
  }

  eventsRetry.addEventListener("click", loadEvents);
  $("refreshEvents").addEventListener("click", loadEvents);

  // ---------------- Register dialog ----------------

  function openRegisterDialog(ev) {
    activeEvent = ev;
    registerStep.hidden = false;
    confirmStep.hidden = true;
    registerError.hidden = true;
    registerForm.reset();
    if (lastRegisteredEmail) regEmail.value = lastRegisteredEmail;
    dialogEventName.textContent = ev.eventName || ev.eventId;
    dialogEventMeta.textContent = `${fmtDate(ev.eventDate)} · ${ev.location || "Location TBD"}`;
    registerDialog.showModal();
    regName.focus();
  }

  function closeDialog() {
    registerDialog.close();
  }
  dialogClose.addEventListener("click", closeDialog);
  dialogCancel.addEventListener("click", closeDialog);
  confirmDone.addEventListener("click", () => {
    closeDialog();
    loadEvents();
  });

  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!activeEvent) return;

    registerError.hidden = true;
    registerSubmit.disabled = true;
    registerSubmit.textContent = "Reserving…";

    try {
      const body = await api("register", {
        method: "POST",
        body: JSON.stringify({
          eventId: activeEvent.eventId,
          name: regName.value.trim(),
          email: regEmail.value.trim(),
        }),
      });

      lastRegisteredEmail = body.email;
      registerStep.hidden = true;
      confirmStep.hidden = false;
      confirmEventName.textContent = activeEvent.eventName || activeEvent.eventId;
      confirmEventMeta.textContent = `${fmtDate(activeEvent.eventDate)} · ${activeEvent.location || ""}`;
      confirmId.textContent = body.registrationId;
    } catch (err) {
      registerError.hidden = false;
      registerError.textContent = err.status === 409
        ? "This event just filled up — try another one."
        : err.status === 404
        ? "This event is no longer available."
        : err.message || "Couldn't complete registration. Try again.";
    } finally {
      registerSubmit.disabled = false;
      registerSubmit.textContent = "Confirm seat";
    }
  });

  // ---------------- My tickets ----------------

  function ticketCard(reg) {
    const card = document.createElement("article");
    card.className = "stub-card ticket-card";
    const cancelled = reg.status === "CANCELLED";

    card.innerHTML = `
      <div class="stub-main">
        <span class="status-tag${cancelled ? " cancelled" : ""}">${cancelled ? "Cancelled" : "Confirmed"}</span>
        <p class="stub-title">${escapeHtml(reg.eventId)}</p>
        <p class="stub-meta">Registered ${escapeHtml((reg.createdAt || "").slice(0, 10))}</p>
      </div>
      <div class="stub-notch stub-notch-top"></div>
      <div class="stub-notch stub-notch-bottom"></div>
      <div class="stub-tear"></div>
      <div class="stub-side">
        <p class="stub-code">ID</p>
        <p class="stub-seat" style="font-size:14px; font-family:var(--font-mono);">${reg.registrationId.slice(0, 8)}</p>
      </div>
      <div class="event-actions">
        <button class="btn btn-small btn-ghost" type="button">Cancel ticket</button>
      </div>
    `;

    const cancelBtn = card.querySelector("button");
    cancelBtn.addEventListener("click", () => cancelTicket(reg.registrationId, card, cancelBtn));
    return card;
  }

  async function cancelTicket(id, card, btn) {
    if (btn.dataset.confirming !== "yes") {
      btn.dataset.confirming = "yes";
      btn.textContent = "Confirm cancel?";
      setTimeout(() => {
        if (btn.dataset.confirming === "yes") {
          btn.dataset.confirming = "";
          btn.textContent = "Cancel ticket";
        }
      }, 3000);
      return;
    }

    btn.disabled = true;
    btn.textContent = "Cancelling…";
    try {
      await api(`registration/${encodeURIComponent(id)}`, { method: "DELETE" });
      card.style.transition = "opacity 0.25s ease";
      card.style.opacity = "0";
      setTimeout(() => card.remove(), 250);
      showToast("Ticket cancelled");
    } catch (err) {
      showToast(err.message || "Couldn't cancel ticket");
      btn.disabled = false;
      btn.dataset.confirming = "";
      btn.textContent = "Cancel ticket";
    }
  }

  lookupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = lookupEmail.value.trim();
    ticketsGrid.innerHTML = "";
    ticketsState.hidden = true;

    try {
      const data = await api(`registrations/${encodeURIComponent(email)}`);
      const regs = data.registrations || [];
      if (regs.length === 0) {
        ticketsState.hidden = false;
        ticketsStateText.textContent = "No tickets found for that email yet.";
        return;
      }
      regs.forEach((r) => ticketsGrid.appendChild(ticketCard(r)));
    } catch (err) {
      ticketsState.hidden = false;
      ticketsStateText.textContent = err.message || "Couldn't look up tickets. Try again.";
    }
  });

  loadEvents();
})();
