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

document.addEventListener("DOMContentLoaded", () => {
  const connectionStatus = document.querySelector("#connection-status");
  if (connectionStatus) {
    const showConnectionState = () => {
      connectionStatus.hidden = navigator.onLine;
    };
    window.addEventListener("online", showConnectionState);
    window.addEventListener("offline", showConnectionState);
    showConnectionState();
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
