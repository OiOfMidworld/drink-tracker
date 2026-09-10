(function () {
  const modal = document.getElementById("log-modal");
  if (!modal) return;

  const modalDate = document.getElementById("modal-date");
  const countInput = document.getElementById("drink-count-input");
  const journalInput = document.getElementById("journal-input");
  const modalError = document.getElementById("modal-error");
  const saveBtn = document.getElementById("save-btn");
  const clearBtn = document.getElementById("clear-btn");
  const cancelBtn = document.getElementById("cancel-btn");
  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

  let activeCell = null;

  function showError(message) {
    modalError.textContent = message;
    modalError.hidden = false;
  }

  function openModal(cell) {
    activeCell = cell;
    const dateStr = cell.dataset.date;
    const [y, m, d] = dateStr.split("-");
    modalDate.textContent = `${m}/${d}/${y}`;
    countInput.value = cell.dataset.count || "";
    journalInput.value = cell.dataset.note || "";
    modalError.hidden = true;
    modal.hidden = false;
    countInput.focus();
  }

  function closeModal() {
    modal.hidden = true;
    activeCell = null;
  }

  async function submitEntry(payload) {
    if (!activeCell) return;
    const dateStr = activeCell.dataset.date;

    try {
      const response = await fetch("/api/log", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ date: dateStr, ...payload }),
      });

      const data = await response.json();

      if (!response.ok) {
        showError(data.error || "Something went wrong.");
        return;
      }

      window.location.reload();
    } catch (err) {
      showError("Could not save. Check your connection and try again.");
    }
  }

  document.querySelectorAll(".day-cell:not(.empty):not(.future)").forEach((cell) => {
    cell.addEventListener("click", () => openModal(cell));
  });

  saveBtn.addEventListener("click", () => {
    const raw = countInput.value.trim();
    const payload = { note: journalInput.value };

    if (raw !== "") {
      const count = Number(raw);
      if (!Number.isInteger(count) || count < 0) {
        showError("Enter a whole number of 0 or more.");
        return;
      }
      payload.count = count;
    }

    submitEntry(payload);
  });

  clearBtn.addEventListener("click", () => submitEntry({ count: null }));
  cancelBtn.addEventListener("click", closeModal);

  countInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      saveBtn.click();
    }
  });

  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  function openFromQueryParam() {
    const params = new URLSearchParams(window.location.search);
    const day = params.get("open");
    if (!day) return;

    const table = document.querySelector("table.calendar");
    if (!table) return;

    const iso = `${table.dataset.year}-${table.dataset.month.padStart(2, "0")}-${day.padStart(2, "0")}`;
    const cell = document.querySelector(`.day-cell[data-date="${iso}"]:not(.empty):not(.future)`);
    if (cell) openModal(cell);

    const url = new URL(window.location);
    url.searchParams.delete("open");
    window.history.replaceState({}, "", url);
  }

  openFromQueryParam();
})();
