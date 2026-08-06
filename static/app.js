const colourThemes = ["black", "blue", "pink", "green"];

function readSavedColourTheme() {
  try {
    const savedTheme = window.localStorage.getItem("kindlelise-colour-theme");
    return colourThemes.includes(savedTheme) ? savedTheme : "black";
  } catch (error) {
    return "black";
  }
}

function applyColourTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try {
    window.localStorage.setItem("kindlelise-colour-theme", theme);
  } catch (error) {
    // The selected theme still applies when browser storage is unavailable.
  }
}

applyColourTheme(readSavedColourTheme());

// Preserve the original draft and return a suggestion without ever submitting a message.
async function requestMessageDraftEditSuggestion(conversationId, draft, editingGoal) {
  const csrfInput = document.querySelector("[name='csrfmiddlewaretoken']");
  if (!csrfInput) {
    throw new Error("Draft edit unavailable");
  }
  const formValues = new URLSearchParams({
    draft: draft,
    editing_goal: editingGoal,
  });
  const response = await fetch(
    `/conversations/${encodeURIComponent(conversationId)}/message-edit-suggestion/`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "X-CSRFToken": csrfInput.value,
      },
      body: formValues.toString(),
    },
  );
  if (!response.ok) {
    throw new Error("Draft edit unavailable");
  }
  const responseValues = await response.json();
  if (typeof responseValues.suggestion !== "string" || !responseValues.suggestion.trim()) {
    throw new Error("Draft edit unavailable");
  }
  return responseValues.suggestion;
}

// Show both drafts and replace the text box only after explicit acceptance, never sending it.
function showMessageDraftEditSuggestion(originalDraft, suggestedDraft) {
  const draftField = document.querySelector("#id_body");
  const suggestionPanel = document.querySelector("#message-edit-suggestion");
  const originalText = document.querySelector("#message-edit-original");
  const suggestedText = document.querySelector("#message-edit-suggested");
  const keepButton = document.querySelector("#message-edit-keep");
  const useButton = document.querySelector("#message-edit-use");
  if (!draftField || !suggestionPanel || !originalText || !suggestedText || !keepButton || !useButton) {
    return;
  }
  originalText.textContent = originalDraft;
  suggestedText.textContent = suggestedDraft;
  suggestionPanel.hidden = false;
  keepButton.onclick = () => {
    suggestionPanel.hidden = true;
    draftField.focus();
  };
  useButton.onclick = () => {
    draftField.value = suggestedDraft;
    suggestionPanel.hidden = true;
    draftField.focus();
  };
}

// Fetch public metadata only after the user asks, preserving every editable field.
async function requestPlanMetadata(fetchUrl, publicUrl, csrfToken) {
  const response = await fetch(fetchUrl, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
      "X-CSRFToken": csrfToken,
    },
    body: new URLSearchParams({ public_url: publicUrl }).toString(),
  });
  if (!response.ok) {
    throw new Error("Plan details unavailable");
  }
  const responseValues = await response.json();
  if (
    typeof responseValues.public_place !== "string"
    || typeof responseValues.metadata_token !== "string"
    || typeof responseValues.thumbnail_preview !== "string"
  ) {
    throw new Error("Plan details unavailable");
  }
  return responseValues;
}

document.addEventListener("DOMContentLoaded", () => {
  const themeButton = document.querySelector("[data-theme-toggle]");
  if (themeButton) {
    const updateThemeButtonLabel = () => {
      const currentTheme = document.documentElement.dataset.theme || "black";
      themeButton.setAttribute(
        "aria-label",
        `Colour theme: ${currentTheme}. Change colour theme`,
      );
    };
    updateThemeButtonLabel();
    themeButton.addEventListener("click", () => {
      const currentTheme = document.documentElement.dataset.theme || "black";
      const currentIndex = colourThemes.indexOf(currentTheme);
      applyColourTheme(colourThemes[(currentIndex + 1) % colourThemes.length]);
      updateThemeButtonLabel();
    });
  }

  const notificationContainer = document.querySelector(".messages");
  notificationContainer?.querySelectorAll(".message").forEach((message) => {
    window.setTimeout(() => {
      message.classList.add("is-dismissing");
      window.setTimeout(() => {
        message.remove();
        if (!notificationContainer.children.length) {
          notificationContainer.remove();
        }
      }, 200);
    }, 5000);
  });

  const connectionStatus = document.querySelector("#connection-status");
  if (connectionStatus) {
    const showConnectionState = () => {
      connectionStatus.hidden = navigator.onLine;
    };
    window.addEventListener("online", showConnectionState);
    window.addEventListener("offline", showConnectionState);
    showConnectionState();
  }

  const filterForm = document.querySelector(".discovery-filter-form");
  if (filterForm) {
    const filterTriggers = filterForm.querySelectorAll("[data-filter-target]");
    const filterPanels = filterForm.querySelectorAll(".discovery-filter-panel");
    const closeFilterButtons = filterForm.querySelectorAll("[data-filter-close]");
    const showFilterPanel = (panelId) => {
      filterPanels.forEach((panel) => {
        panel.classList.toggle("is-active", panel.id === panelId);
      });
      filterTriggers.forEach((trigger) => {
        trigger.setAttribute(
          "aria-expanded",
          trigger.dataset.filterTarget === panelId ? "true" : "false",
        );
      });
    };
    filterTriggers.forEach((trigger) => {
      trigger.addEventListener("click", () => {
        const panelId = trigger.dataset.filterTarget;
        showFilterPanel(
          trigger.getAttribute("aria-expanded") === "true" ? null : panelId,
        );
      });
    });
    closeFilterButtons.forEach((button) => {
      button.addEventListener("click", () => showFilterPanel(null));
    });
    filterForm.classList.add("filter-panels-ready");
    const filterErrorPanel = filterForm.querySelector("[data-filter-errors]");
    showFilterPanel(filterErrorPanel ? filterErrorPanel.id : null);
  }

  const metadataButton = document.querySelector("[data-plan-metadata-fetch]");
  const publicUrlField = document.querySelector("#id_public_url");
  const publicPlaceField = document.querySelector("#id_public_place");
  const metadataStatus = document.querySelector("[data-plan-metadata-status]");
  const metadataToken = document.querySelector("[data-plan-metadata-token]");
  const metadataPreview = document.querySelector("[data-plan-metadata-preview]");
  if (
    metadataButton
    && publicUrlField
    && publicPlaceField
    && metadataStatus
    && metadataToken
    && metadataPreview
  ) {
    const clearFetchedMetadata = () => {
      metadataToken.value = "";
      metadataPreview.hidden = true;
      metadataPreview.removeAttribute("src");
      metadataStatus.textContent = "Add the URL, then fetch its public place and image.";
    };
    publicUrlField.addEventListener("input", clearFetchedMetadata);
    metadataButton.addEventListener("click", async () => {
      const publicUrl = publicUrlField.value.trim();
      const csrfInput = metadataButton.closest("form")?.querySelector("[name='csrfmiddlewaretoken']");
      if (!publicUrl) {
        metadataStatus.textContent = "Enter the public HTTPS URL first.";
        publicUrlField.focus();
        return;
      }
      if (!csrfInput) {
        metadataStatus.textContent = "Details could not be fetched. You can enter the place manually.";
        return;
      }
      metadataButton.disabled = true;
      metadataStatus.setAttribute("aria-busy", "true");
      metadataStatus.textContent = "Fetching public place and image…";
      metadataToken.value = "";
      try {
        const metadata = await requestPlanMetadata(
          metadataButton.dataset.fetchUrl,
          publicUrl,
          csrfInput.value,
        );
        if (metadata.public_place) {
          publicPlaceField.value = metadata.public_place;
        }
        metadataToken.value = metadata.metadata_token;
        if (metadata.thumbnail_preview.startsWith("data:image/jpeg;base64,")) {
          metadataPreview.src = metadata.thumbnail_preview;
          metadataPreview.hidden = false;
        } else {
          metadataPreview.hidden = true;
          metadataPreview.removeAttribute("src");
        }
        if (metadata.public_place && metadata.thumbnail_preview) {
          metadataStatus.textContent = "Public place and image found. You can edit the place.";
        } else if (metadata.public_place) {
          metadataStatus.textContent = "Public place found. No usable image was available.";
        } else {
          metadataStatus.textContent = "Image found. Enter the public place manually.";
        }
      } catch (error) {
        metadataPreview.hidden = true;
        metadataPreview.removeAttribute("src");
        metadataStatus.textContent = "Details could not be fetched. You can enter the place manually.";
      } finally {
        metadataStatus.removeAttribute("aria-busy");
        metadataButton.disabled = false;
      }
    });
  }

  const draftField = document.querySelector("#id_body");
  const statusText = document.querySelector("#message-edit-status");
  const editButtons = document.querySelectorAll("[data-message-edit-goal]");
  if (!draftField || !statusText || !editButtons.length) {
    return;
  }
  editButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const originalDraft = draftField.value;
      if (!originalDraft.trim()) {
        statusText.textContent = "Write a draft before requesting an edit.";
        draftField.focus();
        return;
      }
      statusText.textContent = "Requesting a suggestion…";
      statusText.setAttribute("aria-busy", "true");
      editButtons.forEach((editButton) => { editButton.disabled = true; });
      try {
        const suggestion = await requestMessageDraftEditSuggestion(
          button.dataset.conversationId,
          originalDraft,
          button.dataset.messageEditGoal,
        );
        showMessageDraftEditSuggestion(originalDraft, suggestion);
        statusText.textContent = "Review the suggestion before using it.";
      } catch (error) {
        statusText.textContent = "The draft could not be edited. Your original is unchanged.";
      } finally {
        statusText.removeAttribute("aria-busy");
        editButtons.forEach((editButton) => { editButton.disabled = false; });
      }
    });
  });
});
