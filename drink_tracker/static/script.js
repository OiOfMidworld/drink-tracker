(function () {
  const modal = document.getElementById("log-modal");
  if (!modal) return;

  const modalDate = document.getElementById("modal-date");
  const countInput = document.getElementById("drink-count-input");
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
    modalError.hidden = true;
    modal.hidden = false;
    countInput.focus();
  }

  function closeModal() {
    modal.hidden = true;
    activeCell = null;
  }

  async function submitCount(count) {
    if (!activeCell) return;
    const dateStr = activeCell.dataset.date;

    try {
      const response = await fetch("/api/log", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ date: dateStr, count: count }),
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
    const count = Number(raw);

    if (raw === "" || !Number.isInteger(count) || count < 0) {
      showError("Enter a whole number of 0 or more.");
      return;
    }

    submitCount(count);
  });

  clearBtn.addEventListener("click", () => submitCount(null));
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
})();
