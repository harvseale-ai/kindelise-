// # KEYWORD: DOM — the browser's live copy of the page that JavaScript can read and change.
// # KEYWORD: event listener — waits for a named visitor or browser action, then runs its steps.
// # KEYWORD: local storage — a small browser-owned place used here to remember the chosen colour.
// # KEYWORD: fetch — asks one of this site's addresses for information without opening a new page.

// # WHY: Keeps the permitted colour choices in one list so the button cannot select an unknown theme.
const colourThemes = ["black", "blue", "pink", "green"];

// # WHY: Reads the visitor's previous colour choice while safely falling back when storage is unavailable.
function readSavedColourTheme() {
  // # KEYWORD: try/catch — attempts a step and provides a safe result if that step fails.
  try {
    const savedTheme = window.localStorage.getItem("kindlelise-colour-theme");
    return colourThemes.includes(savedTheme) ? savedTheme : "black";
  } catch (error) {
    return "black";
  }
}

// # WHY: Changes the page colour and remembers it for the visitor's next page.
function applyColourTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try {
    window.localStorage.setItem("kindlelise-colour-theme", theme);
  } catch (error) {
    // The selected theme still applies when browser storage is unavailable.
  }
}

// # WHY: Applies the saved colour before the page is ready so the visitor does not see a colour flash.
applyColourTheme(readSavedColourTheme());

// # KEYWORD: async/await — pauses only this task while a page request finishes, without freezing the page.
// # WHY: Preserves the original draft and returns a suggestion without ever sending the message.
async function requestMessageDraftEditSuggestion(conversationId, draft, editingGoal) {
  // # WHY: Uses the page's private form token so another website cannot request edits as this visitor.
  const csrfInput = document.querySelector("[name='csrfmiddlewaretoken']");
  if (!csrfInput) {
    throw new Error("Draft edit unavailable");
  }
  // # KEYWORD: URLSearchParams — turns labelled values into the same format as a normal web form.
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

// # WHY: Shows both drafts and changes the text box only after the visitor accepts the suggestion.
function showMessageDraftEditSuggestion(originalDraft, suggestedDraft) {
  // # WHY: Collects every part of the review panel before changing anything on the page.
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
  // # WHY: Closes the comparison while leaving the visitor's original words untouched.
  keepButton.onclick = () => {
    suggestionPanel.hidden = true;
    draftField.focus();
  };
  // # WHY: Copies the accepted suggestion into the unsent box but still leaves sending to the visitor.
  useButton.onclick = () => {
    draftField.value = suggestedDraft;
    suggestionPanel.hidden = true;
    draftField.focus();
  };
}

// # WHY: Fetches public plan details only after the visitor asks and keeps every field editable.
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

// # WHY: Waits until the page exists before finding controls and connecting their actions.
document.addEventListener("DOMContentLoaded", () => {
  // # WHY: Finds the colour button once so pages without it can safely skip these steps.
  const themeButton = document.querySelector("[data-theme-toggle]");
  if (themeButton) {
    // # WHY: Gives screen-reader users the current colour and explains what the button will do.
    const updateThemeButtonLabel = () => {
      const currentTheme = document.documentElement.dataset.theme || "black";
      themeButton.setAttribute(
        "aria-label",
        `Colour theme: ${currentTheme}. Change colour theme`,
      );
    };
    updateThemeButtonLabel();
    // # WHY: Moves to the next permitted colour each time the visitor presses the button.
    themeButton.addEventListener("click", () => {
      const currentTheme = document.documentElement.dataset.theme || "black";
      const currentIndex = colourThemes.indexOf(currentTheme);
      applyColourTheme(colourThemes[(currentIndex + 1) % colourThemes.length]);
      updateThemeButtonLabel();
    });
  }

  // # WHY: Finds temporary page messages so they can appear without pushing the main page downward.
  const notificationContainer = document.querySelector(".messages");
  // # WHY: Gives each temporary message five seconds to be read before beginning its exit.
  notificationContainer?.querySelectorAll(".message").forEach((message) => {
    window.setTimeout(() => {
      message.classList.add("is-dismissing");
      // # WHY: Removes the message after its short exit movement has finished.
      window.setTimeout(() => {
        message.remove();
        if (!notificationContainer.children.length) {
          notificationContainer.remove();
        }
      }, 200);
    }, 5000);
  });

  // # WHY: Shows a warning only while the browser reports that its network connection is unavailable.
  const connectionStatus = document.querySelector("#connection-status");
  if (connectionStatus) {
    // # WHY: Keeps the warning in step with the browser's current online state.
    const showConnectionState = () => {
      connectionStatus.hidden = navigator.onLine;
    };
    window.addEventListener("online", showConnectionState);
    window.addEventListener("offline", showConnectionState);
    showConnectionState();
  }

  // # WHY: Finds the discovery filters so other pages do not run discovery-only behaviour.
  const filterForm = document.querySelector(".discovery-filter-form");
  if (filterForm) {
    // # WHY: Stores the filter buttons, panels, and close controls used by the same open-and-close rule.
    const filterTriggers = filterForm.querySelectorAll("[data-filter-target]");
    const filterPanels = filterForm.querySelectorAll(".discovery-filter-panel");
    const closeFilterButtons = filterForm.querySelectorAll("[data-filter-close]");
    // # WHY: Opens one requested filter panel and closes the others so the page stays compact.
    const showFilterPanel = (panelId) => {
      // # WHY: Marks only the requested panel as visible.
      filterPanels.forEach((panel) => {
        panel.classList.toggle("is-active", panel.id === panelId);
      });
      // # WHY: Keeps each button's accessibility state matched to its panel.
      filterTriggers.forEach((trigger) => {
        trigger.setAttribute(
          "aria-expanded",
          trigger.dataset.filterTarget === panelId ? "true" : "false",
        );
      });
    };
    // # WHY: Lets each filter button open its panel or close it when pressed again.
    filterTriggers.forEach((trigger) => {
      trigger.addEventListener("click", () => {
        const panelId = trigger.dataset.filterTarget;
        showFilterPanel(
          trigger.getAttribute("aria-expanded") === "true" ? null : panelId,
        );
      });
    });
    // # WHY: Gives every Close button the same way to hide all filter panels.
    closeFilterButtons.forEach((button) => {
      button.addEventListener("click", () => showFilterPanel(null));
    });
    filterForm.classList.add("filter-panels-ready");
    // # WHY: Opens a panel containing a form error so the visitor can immediately correct it.
    const filterErrorPanel = filterForm.querySelector("[data-filter-errors]");
    showFilterPanel(filterErrorPanel ? filterErrorPanel.id : null);
  }

  // # WHY: Collects the create-plan controls needed to fetch and preview public place details.
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
    // # WHY: Removes old fetched details when the public address changes so they cannot be saved by mistake.
    const clearFetchedMetadata = () => {
      metadataToken.value = "";
      metadataPreview.hidden = true;
      metadataPreview.removeAttribute("src");
      metadataStatus.textContent = "Add the URL, then fetch its public place and image.";
    };
    // # WHY: Clears the preview as soon as the visitor edits its source address.
    publicUrlField.addEventListener("input", clearFetchedMetadata);
    // # WHY: Fetches the public place and image only after the visitor presses Fetch details.
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
      // # WHY: Keeps the form usable with a clear fallback if the outside public page cannot be read.
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
        // # KEYWORD: finally — runs cleanup whether the attempted request worked or failed.
        metadataStatus.removeAttribute("aria-busy");
        metadataButton.disabled = false;
      }
    });
  }

  // # WHY: Collects the unsent-message controls used to request and review wording changes.
  const draftField = document.querySelector("#id_body");
  const statusText = document.querySelector("#message-edit-status");
  const editButtons = document.querySelectorAll("[data-message-edit-goal]");
  if (!draftField || !statusText || !editButtons.length) {
    return;
  }
  // # WHY: Gives each wording button the same request, review, and error behaviour.
  editButtons.forEach((button) => {
    // # WHY: Requests a suggestion for the chosen goal without sending or replacing the draft automatically.
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
      // # WHY: Restores usable controls whether the wording service answers or fails.
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
