(function () {
  const form = document.getElementById("booking-form");
  if (!form) return;

  const dateInput = document.getElementById("id_date");
  const slotsBox = document.getElementById("slots");
  const message = document.getElementById("slot-message");
  const hiddenTime = document.getElementById("selected-time");
  const bookBtn = document.getElementById("book-btn");
  const slotsUrl = form.dataset.slotsUrl;

  let requestId = 0; // ignores slow responses from an older date

  function resetSelection() {
    hiddenTime.value = "";
    bookBtn.disabled = true;
    slotsBox.innerHTML = "";
  }

  function selectSlot(button, time) {
    slotsBox.querySelectorAll(".slot").forEach((b) => b.classList.remove("selected"));
    button.classList.add("selected");
    hiddenTime.value = time;
    bookBtn.disabled = false;
  }

  async function loadSlots() {
    resetSelection();

    if (!dateInput.value) {
      message.textContent = "Pick a date to see free slots.";
      return;
    }

    const current = ++requestId;
    message.textContent = "Loading slots...";

    try {
      const response = await fetch(`${slotsUrl}?date=${encodeURIComponent(dateInput.value)}`);
      const data = await response.json();
      if (current !== requestId) return;

      if (!response.ok) {
        message.textContent = data.error || "Could not load slots.";
        return;
      }

      if (data.slots.length === 0) {
        message.textContent = "No free slots on this date. Try another day.";
        return;
      }

      message.textContent = "Select a time:";
      data.slots.forEach((time) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "slot";
        button.textContent = time;
        button.addEventListener("click", () => selectSlot(button, time));
        slotsBox.appendChild(button);
      });
    } catch (error) {
      if (current === requestId) {
        message.textContent = "Could not load slots. Please try again.";
      }
    }
  }

  dateInput.addEventListener("change", loadSlots);

  // If the page re-opens with a date (after a form error), load its slots
  if (dateInput.value) loadSlots();
})();