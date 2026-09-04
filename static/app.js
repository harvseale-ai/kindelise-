// # KEYWORD: DOM — the browser's live copy of the page that JavaScript can read and change.
// # KEYWORD: event listener — waits for a named visitor or browser action, then runs its steps.
// # KEYWORD: local storage — a small browser-owned place used here to remember the chosen colour.
// # KEYWORD: fetch — asks one of this site's addresses for information without opening a new page.

// =============================================================================
// COLOUR THEME
// Reads, applies, and remembers the visitor's chosen colour theme.
// =============================================================================

// # WHY: Keeps the permitted colour choices in one list so the button cannot select an unknown theme.
const colourThemes = ["light", "dark"];
const legacyDarkThemes = ["black", "blue", "pink", "green"];

// # WHY: Reads the visitor's previous colour choice while safely falling back when storage is unavailable.
function readSavedColourTheme() {
  // # KEYWORD: try/catch — attempts a step and provides a safe result if that step fails.
  try {
    const savedTheme = window.localStorage.getItem("kindlelise-colour-theme");
    if (legacyDarkThemes.includes(savedTheme)) {
      return "dark";
    }
    return colourThemes.includes(savedTheme) ? savedTheme : "light";
  } catch (error) {
    return "light";
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

// =============================================================================
// MESSAGE WRITING SUGGESTIONS
// Requests and presents optional wording changes for an unsent message.
// =============================================================================

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

// =============================================================================
// PLAN PUBLIC DETAILS
// Requests the public place name and preview image used by plan forms.
// =============================================================================

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
    || typeof responseValues.public_address !== "string"
    || typeof responseValues.metadata_token !== "string"
    || typeof responseValues.thumbnail_preview !== "string"
  ) {
    throw new Error("Plan details unavailable");
  }
  return responseValues;
}

// # WHY: Requests editable plan wording from already-entered facts without creating or submitting the plan.
async function requestPlanDraft(draftUrl, planFacts, csrfToken) {
  const response = await fetch(draftUrl, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
      "X-CSRFToken": csrfToken,
    },
    body: new URLSearchParams(planFacts).toString(),
  });
  if (!response.ok) {
    throw new Error("Plan draft unavailable");
  }
  const responseValues = await response.json();
  if (
    typeof responseValues.title !== "string"
    || typeof responseValues.description !== "string"
    || typeof responseValues.public_place !== "string"
    || typeof responseValues.public_address !== "string"
    || typeof responseValues.date !== "string"
    || typeof responseValues.time !== "string"
    || !responseValues.title.trim()
    || !responseValues.description.trim()
  ) {
    throw new Error("Plan draft unavailable");
  }
  return responseValues;
}

// =============================================================================
// PAGE CONTROLS
// Connects page controls only after the HTML is ready.
// =============================================================================

// # WHY: Waits until the page exists before finding controls and connecting their actions.
document.addEventListener("DOMContentLoaded", () => {
  // ---------------------------------------------------------------------------
  // TEMPORARY WORDMARK
  // Reveals the handwritten name briefly when the shared top bar is explored.
  // ---------------------------------------------------------------------------

  const siteHeader = document.querySelector(".site-header");
  if (siteHeader) {
    const wordmark = siteHeader.querySelector(".brand-wordmark");
    const wordmarkFontClasses = [
      "wordmark-font-rock-salt",
      "wordmark-font-caveat-brush",
      "wordmark-font-kalam",
      "wordmark-font-patrick-hand",
      "wordmark-font-gloria",
    ];
    let wordmarkTimer;
    let previousWordmarkFont = -1;
    const chooseWordmarkFont = () => {
      if (!wordmark) {
        return;
      }
      let nextFont = Math.floor(Math.random() * wordmarkFontClasses.length);
      if (nextFont === previousWordmarkFont) {
        nextFont = (nextFont + 1) % wordmarkFontClasses.length;
      }
      wordmark.classList.remove(...wordmarkFontClasses);
      wordmark.classList.add(wordmarkFontClasses[nextFont]);
      previousWordmarkFont = nextFont;
    };
    const revealWordmark = () => {
      if (!siteHeader.classList.contains("is-wordmark-visible")) {
        chooseWordmarkFont();
      }
      siteHeader.classList.add("is-wordmark-visible");
      window.clearTimeout(wordmarkTimer);
      wordmarkTimer = window.setTimeout(() => {
        siteHeader.classList.remove("is-wordmark-visible");
      }, 20000);
    };
    siteHeader.addEventListener("pointerenter", revealWordmark);
    siteHeader.addEventListener("focusin", revealWordmark);
  }

  // ---------------------------------------------------------------------------
  // COLOUR THEME CONTROL
  // Connects the top-bar button that cycles through the permitted themes.
  // ---------------------------------------------------------------------------

  // # WHY: Finds the colour button once so pages without it can safely skip these steps.
  const themeButton = document.querySelector("[data-theme-toggle]");
  if (themeButton) {
    // # WHY: Gives screen-reader users the current colour and explains what the button will do.
    const updateThemeButtonLabel = () => {
      const currentTheme = document.documentElement.dataset.theme || "light";
      const nextTheme = currentTheme === "dark" ? "light" : "dark";
      themeButton.setAttribute(
        "aria-label",
        `Use ${nextTheme} mode`,
      );
      themeButton.setAttribute("title", `Use ${nextTheme} mode`);
    };
    updateThemeButtonLabel();
    // # WHY: Moves to the next permitted colour each time the visitor presses the button.
    themeButton.addEventListener("click", () => {
      const currentTheme = document.documentElement.dataset.theme || "light";
      const currentIndex = colourThemes.indexOf(currentTheme);
      applyColourTheme(colourThemes[(currentIndex + 1) % colourThemes.length]);
      updateThemeButtonLabel();
    });
  }

  // ---------------------------------------------------------------------------
  // GUIDE CARD LOOP
  // Rotates authorised plan cards through the Guide feature.
  // ---------------------------------------------------------------------------

  document.querySelectorAll("[data-guide-card-loop]").forEach((guideCardLoop) => {
    const guideCards = Array.from(
      guideCardLoop.querySelectorAll("[data-guide-card]"),
    );
    const requestedVisibleCards = Number.parseInt(
      guideCardLoop.dataset.guideVisibleCards || "3",
      10,
    );
    const visibleGuideCards = Math.min(requestedVisibleCards, guideCards.length);
    let firstGuideCard = 0;

    const showGuideCards = () => {
      const visibleIndexes = new Set();
      for (let offset = 0; offset < visibleGuideCards; offset += 1) {
        visibleIndexes.add((firstGuideCard + offset) % guideCards.length);
      }
      guideCards.forEach((card, index) => {
        card.hidden = !visibleIndexes.has(index);
      });
    };

    if (guideCards.length > visibleGuideCards) {
      window.setInterval(() => {
        if (
          document.hidden ||
          guideCardLoop.matches(":hover") ||
          guideCardLoop.contains(document.activeElement)
        ) return;
        firstGuideCard = (
          firstGuideCard + visibleGuideCards
        ) % guideCards.length;
        showGuideCards();
      }, 10000);
    }
  });

  // # WHY: Loads the small plan-preview film only after its preceding purpose statement has left view.
  const guidePlanVideoTrigger = document.querySelector("[data-guide-plan-video-trigger]");
  const guidePlanVideoCard = document.querySelector("[data-guide-plan-video-card]");
  const guidePlanVideo = guidePlanVideoCard?.querySelector("[data-guide-plan-video]");
  if (guidePlanVideoTrigger && guidePlanVideoCard && guidePlanVideo) {
    let guidePlanVideoPlayed = false;
    const playGuidePlanVideo = () => {
      if (
        guidePlanVideoPlayed ||
        guidePlanVideoTrigger.getBoundingClientRect().bottom > 0 ||
        window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ) return;
      guidePlanVideoPlayed = true;
      window.removeEventListener("scroll", playGuidePlanVideo);
      guidePlanVideo.src = guidePlanVideo.dataset.src;
      guidePlanVideo.load();
      guidePlanVideo.play().then(() => {
        guidePlanVideoCard.classList.add("is-playing");
      }).catch(() => {});
    };
    guidePlanVideo.addEventListener("ended", () => {
      guidePlanVideoCard.classList.remove("is-playing");
      guidePlanVideoCard.classList.add("is-finished");
    });
    window.addEventListener("scroll", playGuidePlanVideo, { passive: true });
    playGuidePlanVideo();
  }

  // ---------------------------------------------------------------------------
  // GUIDE VIDEO LOOP
  // Plays the lightweight Guide films in sequence without loading them all at once.
  // ---------------------------------------------------------------------------

  const guideVideoLoop = document.querySelector("[data-guide-video-loop]");
  if (guideVideoLoop) {
    const guideVideos = Array.from(
      guideVideoLoop.querySelectorAll("[data-guide-video]"),
    );
    const guideVideoToggle = guideVideoLoop.querySelector("[data-guide-video-toggle]");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let activeGuideVideo = 0;
    let guideVideosPaused = reduceMotion.matches;

    const updateGuideVideoToggle = () => {
      if (!guideVideoToggle) return;
      const label = guideVideosPaused ? "Play video" : "Pause video";
      guideVideoToggle.textContent = guideVideosPaused ? "Play" : "Pause";
      guideVideoToggle.setAttribute("aria-label", label);
    };

    const showGuideVideo = (nextIndex) => {
      const currentVideo = guideVideos[activeGuideVideo];
      const nextVideo = guideVideos[nextIndex];
      if (!nextVideo || nextVideo === currentVideo) return;
      if (!nextVideo.currentSrc && nextVideo.dataset.guideVideoSrc) {
        nextVideo.src = nextVideo.dataset.guideVideoSrc;
        nextVideo.load();
      }
      nextVideo.currentTime = 0;
      const playRequest = nextVideo.play();
      playRequest?.then(() => {
        currentVideo.pause();
        currentVideo.classList.remove("is-active");
        nextVideo.classList.add("is-active");
        activeGuideVideo = nextIndex;
      }).catch(() => {});
    };

    guideVideos.forEach((video, index) => {
      video.addEventListener("ended", () => {
        if (guideVideosPaused) return;
        showGuideVideo((index + 1) % guideVideos.length);
      });
    });

    if (guideVideosPaused) {
      guideVideos[activeGuideVideo]?.pause();
    } else {
      guideVideos[activeGuideVideo]?.play().catch(() => {});
    }
    updateGuideVideoToggle();

    guideVideoToggle?.addEventListener("click", () => {
      guideVideosPaused = !guideVideosPaused;
      const currentVideo = guideVideos[activeGuideVideo];
      if (guideVideosPaused) {
        currentVideo?.pause();
      } else {
        currentVideo?.play().catch(() => {});
      }
      updateGuideVideoToggle();
    });

    document.addEventListener("visibilitychange", () => {
      const currentVideo = guideVideos[activeGuideVideo];
      if (document.hidden) {
        currentVideo?.pause();
      } else if (!guideVideosPaused) {
        currentVideo?.play().catch(() => {});
      }
    });
  }

  // ---------------------------------------------------------------------------
  // TEMPORARY NOTICES AND CONNECTION STATUS
  // Dismisses page notices and keeps the offline warning current.
  // ---------------------------------------------------------------------------

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

  // ---------------------------------------------------------------------------
  // EXPANDABLE FILTERS
  // Opens one discovery or plan filter panel at a time and reveals form errors.
  // ---------------------------------------------------------------------------

  // # WHY: Finds the page's expandable filter group without affecting pages that do not use one.
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

  // ---------------------------------------------------------------------------
  // OPEN PLAN SEARCH
  // Filters the authorised plan cards already on the page and offers a compact
  // keyboard-friendly result list without creating a second search endpoint.
  // ---------------------------------------------------------------------------

  // # WHY: Limits this behaviour to the plans page and reuses only cards the server has already permitted.
  const planSearch = document.querySelector("[data-plan-search]");
  if (planSearch) {
    const searchInput = planSearch.querySelector(".plan-search-input");
    const clearSearch = planSearch.querySelector("[data-plan-search-clear]");
    const suggestions = planSearch.querySelector("[data-plan-search-suggestions]");
    const searchStatus = planSearch.querySelector("[data-plan-search-status]");
    const planCards = Array.from(document.querySelectorAll(".plans-grid .plan-card"));
    const liveEmptyState = document.querySelector("[data-plan-search-empty]");
    const serverEmptyState = document.querySelector(".plans-empty-state:not([data-plan-search-empty])");
    const initialSearch = searchInput?.value.trim() || "";
    const searchUrl = planSearch.dataset.planSearchUrl;
    let activeSuggestion = -1;
    let remoteSearchTimer = null;
    let remoteSearchSequence = 0;

    // # WHY: Adds emphasis with text nodes instead of inserting untrusted plan or query HTML.
    const appendHighlightedText = (container, value, query) => {
      const lowerValue = value.toLocaleLowerCase();
      const lowerQuery = query.toLocaleLowerCase();
      let cursor = 0;
      let matchIndex = lowerValue.indexOf(lowerQuery);
      while (matchIndex !== -1) {
        container.append(document.createTextNode(value.slice(cursor, matchIndex)));
        const highlight = document.createElement("mark");
        highlight.textContent = value.slice(matchIndex, matchIndex + query.length);
        container.append(highlight);
        cursor = matchIndex + query.length;
        matchIndex = lowerValue.indexOf(lowerQuery, cursor);
      }
      container.append(document.createTextNode(value.slice(cursor)));
    };

    // # WHY: Keeps the combobox state and visible active result in sync for keyboard users.
    const setActiveSuggestion = (nextIndex) => {
      const rows = Array.from(suggestions.querySelectorAll(".plan-search-suggestion"));
      if (!rows.length) {
        activeSuggestion = -1;
        searchInput.removeAttribute("aria-activedescendant");
        return;
      }
      activeSuggestion = (nextIndex + rows.length) % rows.length;
      rows.forEach((row, index) => row.classList.toggle("is-active", index === activeSuggestion));
      searchInput.setAttribute("aria-activedescendant", rows[activeSuggestion].id);
      rows[activeSuggestion].scrollIntoView({ block: "nearest" });
    };

    // # WHY: Closes the floating list without changing the filtered plan grid below it.
    const closeSuggestions = () => {
      suggestions.hidden = true;
      suggestions.replaceChildren();
      searchInput.setAttribute("aria-expanded", "false");
      searchInput.removeAttribute("aria-activedescendant");
      activeSuggestion = -1;
    };

    // # WHY: Uses one result renderer for both cards already on Plans and authorised results fetched elsewhere.
    const renderSuggestionList = (matches, query) => {
      suggestions.replaceChildren();
      matches.slice(0, 6).forEach((card, index) => {
        const row = document.createElement("li");
        row.className = "plan-search-suggestion";
        row.id = `plan-search-suggestion-${index}`;
        row.setAttribute("role", "option");
        const link = document.createElement("a");
        link.href = card.href;
        if (card.dataset.planImage) {
          const image = document.createElement("img");
          image.src = card.dataset.planImage;
          image.alt = "";
          link.append(image);
        } else {
          const imagePlaceholder = document.createElement("span");
          imagePlaceholder.className = "plan-search-suggestion-image";
          imagePlaceholder.setAttribute("aria-hidden", "true");
          link.append(imagePlaceholder);
        }
        const copy = document.createElement("span");
        copy.className = "plan-search-suggestion-copy";
        const title = document.createElement("strong");
        appendHighlightedText(title, card.dataset.planTitle, query);
        const detail = document.createElement("span");
        detail.textContent = `${card.dataset.planPlace} · ${card.dataset.planDate}`;
        copy.append(title, detail);
        link.append(copy);
        row.append(link);
        suggestions.append(row);
      });
      activeSuggestion = -1;
      suggestions.hidden = !matches.length;
      searchInput.setAttribute("aria-expanded", matches.length ? "true" : "false");
    };

    // # WHY: Loads the same bounded open-plan suggestions when the current page has no plan grid to reuse.
    const requestGlobalSuggestions = (query, fallbackMatches) => {
      window.clearTimeout(remoteSearchTimer);
      const requestSequence = ++remoteSearchSequence;
      remoteSearchTimer = window.setTimeout(async () => {
        try {
          const requestUrl = new URL(searchUrl, window.location.origin);
          requestUrl.searchParams.set("q", query);
          const response = await fetch(requestUrl, {
            credentials: "same-origin",
            headers: { Accept: "application/json" },
          });
          if (!response.ok) throw new Error("Search unavailable");
          const payload = await response.json();
          if (requestSequence !== remoteSearchSequence || searchInput.value.trim() !== query) return;
          const remoteMatches = Array.isArray(payload.results) ? payload.results.map((result) => ({
            href: result.url,
            dataset: {
              planImage: result.image_url || "",
              planTitle: result.title,
              planPlace: result.place,
              planDate: result.date,
            },
          })) : [];
          searchStatus.textContent = `${remoteMatches.length} open plan${remoteMatches.length === 1 ? "" : "s"} found.`;
          renderSuggestionList(remoteMatches, query);
        } catch (error) {
          if (requestSequence === remoteSearchSequence) renderSuggestionList(fallbackMatches, query);
        }
      }, 140);
    };

    // # WHY: Searches only marked open cards, displays at most six quick results, and leaves the full grid as the durable result view.
    const renderPlanSearch = () => {
      const query = searchInput.value.trim();
      const lowerQuery = query.toLocaleLowerCase();
      clearSearch.hidden = !query;
      if (query.length < 2) {
        window.clearTimeout(remoteSearchTimer);
        remoteSearchSequence += 1;
        planCards.forEach((card) => { card.closest("li").hidden = false; });
        if (liveEmptyState) liveEmptyState.hidden = true;
        if (serverEmptyState) serverEmptyState.hidden = false;
        searchStatus.textContent = query ? "Type one more character to search open plans." : "";
        closeSuggestions();
        return;
      }

      const matches = planCards.filter((card) => (
        card.hasAttribute("data-plan-searchable")
        && card.dataset.planSearchText.toLocaleLowerCase().includes(lowerQuery)
      ));
      planCards.forEach((card) => {
        card.closest("li").hidden = !matches.includes(card);
      });
      if (serverEmptyState) serverEmptyState.hidden = true;
      if (liveEmptyState) liveEmptyState.hidden = matches.length > 0;
      searchStatus.textContent = `${matches.length} open plan${matches.length === 1 ? "" : "s"} found.`;
      renderSuggestionList(matches, query);
      requestGlobalSuggestions(query, matches);
    };

    searchInput.addEventListener("input", renderPlanSearch);
    searchInput.addEventListener("keydown", (event) => {
      const rows = Array.from(suggestions.querySelectorAll(".plan-search-suggestion"));
      if (event.key === "ArrowDown" && rows.length) {
        event.preventDefault();
        setActiveSuggestion(activeSuggestion + 1);
      } else if (event.key === "ArrowUp" && rows.length) {
        event.preventDefault();
        setActiveSuggestion(activeSuggestion < 0 ? rows.length - 1 : activeSuggestion - 1);
      } else if (event.key === "Enter" && activeSuggestion >= 0) {
        event.preventDefault();
        rows[activeSuggestion].querySelector("a").click();
      } else if (event.key === "Escape") {
        closeSuggestions();
      }
    });
    searchInput.addEventListener("focus", () => {
      searchInput.placeholder = searchInput.dataset.activePlaceholder || "Search open plans";
      if (searchInput.value.trim().length >= 2) renderPlanSearch();
    });
    searchInput.addEventListener("blur", () => {
      searchInput.placeholder = searchInput.dataset.idlePlaceholder || "kindlise";
    });
    clearSearch.addEventListener("click", () => {
      searchInput.value = "";
      if (initialSearch) {
        const clearedUrl = new URL(window.location.href);
        clearedUrl.searchParams.delete("q");
        window.location.assign(clearedUrl);
        return;
      }
      renderPlanSearch();
      searchInput.focus();
    });
    document.addEventListener("click", (event) => {
      if (!planSearch.contains(event.target)) closeSuggestions();
    });
    if (initialSearch) renderPlanSearch();
  }

  // # WHY: Opens a conversation at its newest message while leaving the history available by scrolling upward.
  const conversationThread = document.querySelector(".conversation-thread");
  if (conversationThread) {
    conversationThread.scrollTop = conversationThread.scrollHeight;
  }

  // ---------------------------------------------------------------------------
  // PLAN DETAILS FETCHER
  // Connects the public URL field to optional place and image suggestions.
  // ---------------------------------------------------------------------------

  // # WHY: Collects the create-plan controls needed to fetch and preview public place details.
  const metadataButton = document.querySelector("[data-plan-metadata-fetch]");
  const publicUrlField = document.querySelector("#id_public_url");
  const publicPlaceField = document.querySelector("#id_public_place");
  const publicAddressField = document.querySelector("#id_public_address");
  const metadataStatus = document.querySelector("[data-plan-metadata-status]");
  const metadataToken = document.querySelector("[data-plan-metadata-token]");
  const metadataPreview = document.querySelector("[data-plan-metadata-preview]");
  if (
    metadataButton
    && publicUrlField
    && publicPlaceField
    && publicAddressField
    && metadataStatus
    && metadataToken
    && metadataPreview
  ) {
    // # WHY: Removes old fetched details when the public address changes so they cannot be saved by mistake.
    const clearFetchedMetadata = () => {
      metadataToken.value = "";
      metadataPreview.hidden = true;
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
        if (metadata.public_address) {
          publicAddressField.value = metadata.public_address;
        }
        metadataToken.value = metadata.metadata_token;
        if (metadata.thumbnail_preview.startsWith("data:image/jpeg;base64,")) {
          metadataPreview.src = metadata.thumbnail_preview;
          metadataPreview.hidden = false;
        } else {
          metadataPreview.hidden = true;
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
        metadataStatus.textContent = "Details could not be fetched. You can enter the place manually.";
      } finally {
        // # KEYWORD: finally — runs cleanup whether the attempted request worked or failed.
        metadataStatus.removeAttribute("aria-busy");
        metadataButton.disabled = false;
      }
    });
  }

  // ---------------------------------------------------------------------------
  // PLAN DRAFT GENERATOR
  // Combines the existing venue fetch with one optional, reviewable wording draft.
  // ---------------------------------------------------------------------------

  const createFlow = document.querySelector("[data-plan-create-flow]");
  const generateButton = document.querySelector("[data-plan-generate]");
  if (createFlow && generateButton) {
    const createUrlField = createFlow.querySelector("#id_public_url");
    const createPlaceField = createFlow.querySelector("#id_public_place");
    const createAddressField = createFlow.querySelector("#id_public_address");
    const capacityField = createFlow.querySelector("#id_capacity");
    const dateField = createFlow.querySelector("#id_starts_at_0");
    const timeField = createFlow.querySelector("#id_starts_at_1");
    const ideaField = createFlow.querySelector("#plan-idea");
    const titleField = createFlow.querySelector("#id_title");
    const descriptionField = createFlow.querySelector("#id_description");
    const reviewPanel = createFlow.querySelector("[data-plan-draft-review]");
    const createMetadataStatus = createFlow.querySelector("[data-plan-metadata-status]");
    const createMetadataToken = createFlow.querySelector("[data-plan-metadata-token]");
    const createMetadataPreview = createFlow.querySelector("[data-plan-metadata-preview]");
    const planImageInput = createFlow.querySelector("[data-plan-image-input]");
    const planImageDropzone = createFlow.querySelector("[data-plan-image-dropzone]");
    const previewTitle = createFlow.querySelector("[data-plan-preview-title]");
    const previewDescription = createFlow.querySelector("[data-plan-preview-description]");
    const previewPlace = createFlow.querySelector("[data-plan-preview-place]");
    const csrfInput = createFlow.querySelector("[name='csrfmiddlewaretoken']");
    const requiredControls = [
      createUrlField,
      createPlaceField,
      createAddressField,
      capacityField,
      dateField,
      timeField,
      ideaField,
      titleField,
      descriptionField,
      reviewPanel,
      createMetadataStatus,
      createMetadataToken,
      createMetadataPreview,
      planImageInput,
      planImageDropzone,
      previewTitle,
      previewDescription,
      previewPlace,
      csrfInput,
    ];
    if (requiredControls.every(Boolean)) {
      let localImageUrl = "";
      const showSelectedPlanImage = () => {
        const [selectedImage] = planImageInput.files;
        if (!selectedImage) return;
        if (localImageUrl) URL.revokeObjectURL(localImageUrl);
        localImageUrl = URL.createObjectURL(selectedImage);
        createMetadataToken.value = "";
        createMetadataPreview.src = localImageUrl;
        createMetadataPreview.hidden = false;
        planImageDropzone.hidden = true;
        createMetadataStatus.textContent = "Your uploaded photo will be used for this plan.";
      };
      planImageInput.addEventListener("change", showSelectedPlanImage);
      ["dragenter", "dragover"].forEach((eventName) => {
        planImageDropzone.addEventListener(eventName, () => planImageDropzone.classList.add("is-dragging"));
      });
      ["dragleave", "drop"].forEach((eventName) => {
        planImageDropzone.addEventListener(eventName, () => planImageDropzone.classList.remove("is-dragging"));
      });
      const updateDraftCard = () => {
        previewTitle.textContent = titleField.value.trim() || "Your plan title";
        previewDescription.textContent = descriptionField.value.trim() || ideaField.value.trim() || "Your generated plan description will appear here.";
        previewPlace.textContent = createPlaceField.value.trim() || "Public place";
      };
      // # WHY: Keeps manual title and description available without JavaScript but progressively hides an empty review.
      reviewPanel.hidden = (
        !titleField.value.trim()
        && !descriptionField.value.trim()
        && !reviewPanel.querySelector(".errorlist")
      );
      createUrlField.addEventListener("input", () => {
        createMetadataToken.value = "";
        if (!planImageInput.files.length) {
          createMetadataPreview.hidden = true;
          planImageDropzone.hidden = false;
        }
        createMetadataStatus.textContent = "The venue name and image will be added when you generate the plan.";
      });
      [titleField, descriptionField, createPlaceField, ideaField].forEach((field) => {
        field.addEventListener("input", updateDraftCard);
      });
      updateDraftCard();
      generateButton.addEventListener("click", async () => {
        const controlsToCheck = [createUrlField, capacityField, ideaField];
        const firstEmptyControl = controlsToCheck.find((control) => !control.value.trim());
        if (firstEmptyControl) {
          createMetadataStatus.textContent = "Add the event URL, capacity and what you would like company for first.";
          firstEmptyControl.focus();
          return;
        }

        generateButton.disabled = true;
        generateButton.setAttribute("aria-busy", "true");
        createMetadataStatus.textContent = "Adding venue details and writing your draft…";
        // # WHY: Venue fetching may improve the place and image, but failure never removes manual creation.
        try {
          const metadata = await requestPlanMetadata(
            generateButton.dataset.fetchUrl,
            createUrlField.value.trim(),
            csrfInput.value,
          );
          if (metadata.public_place && !createPlaceField.value.trim()) {
            createPlaceField.value = metadata.public_place;
          }
          if (metadata.public_address && !createAddressField.value.trim()) {
            createAddressField.value = metadata.public_address;
          }
          createMetadataToken.value = metadata.metadata_token;
          if (!planImageInput.files.length && metadata.thumbnail_preview.startsWith("data:image/jpeg;base64,")) {
            createMetadataPreview.src = metadata.thumbnail_preview;
            createMetadataPreview.hidden = false;
            planImageDropzone.hidden = true;
          } else if (!planImageInput.files.length) {
            createMetadataPreview.hidden = true;
            planImageDropzone.hidden = false;
          }
        } catch (error) {
          createMetadataToken.value = "";
          if (!planImageInput.files.length) {
            createMetadataPreview.hidden = true;
            planImageDropzone.hidden = false;
    }
}

  // ---------------------------------------------------------------------------
  // PLAN IMAGE REPLACEMENT
  // Reuses the creation upload field and mock-card preview on the edit page.
  // ---------------------------------------------------------------------------

  document.querySelectorAll("[data-plan-image-editor]").forEach((imageEditor) => {
    const imageInput = imageEditor.querySelector("[data-plan-image-input]");
    const imagePreview = imageEditor.querySelector("[data-plan-edit-image-preview]");
    const imageDropzone = imageEditor.querySelector("[data-plan-edit-image-dropzone]");
    if (!imageInput || !imagePreview || !imageDropzone) return;
    let replacementImageUrl = "";
    imageInput.addEventListener("change", () => {
      const [selectedImage] = imageInput.files;
      if (!selectedImage) return;
      if (replacementImageUrl) URL.revokeObjectURL(replacementImageUrl);
      replacementImageUrl = URL.createObjectURL(selectedImage);
      imagePreview.src = replacementImageUrl;
      imagePreview.hidden = false;
      imageDropzone.querySelector("strong").textContent = "Replacement photo selected";
    });
    ["dragenter", "dragover"].forEach((eventName) => {
      imageDropzone.addEventListener(eventName, () => imageDropzone.classList.add("is-dragging"));
    });
    ["dragleave", "drop"].forEach((eventName) => {
      imageDropzone.addEventListener(eventName, () => imageDropzone.classList.remove("is-dragging"));
    });
  });

        try {
          const draft = await requestPlanDraft(
            createFlow.dataset.draftUrl,
            {
              idea: ideaField.value.trim(),
              public_url: createUrlField.value.trim(),
              public_place: createPlaceField.value.trim(),
              public_address: createAddressField.value.trim(),
              capacity: capacityField.value,
            },
            csrfInput.value,
          );
          titleField.value = draft.title;
          descriptionField.value = draft.description;
          createPlaceField.value = draft.public_place || createPlaceField.value;
          createAddressField.value = draft.public_address || createAddressField.value;
          dateField.value = draft.date;
          timeField.value = draft.time;
          updateDraftCard();
          reviewPanel.hidden = false;
          createMetadataStatus.textContent = "Draft generated. Check the extracted venue, date, time and wording before creating the plan.";
          titleField.focus();
        } catch (error) {
          reviewPanel.hidden = false;
          createMetadataStatus.textContent = "A draft could not be generated. You can write the title and description manually.";
          titleField.focus();
        } finally {
          generateButton.removeAttribute("aria-busy");
          generateButton.disabled = false;
        }
      });
    }
  }

  // ---------------------------------------------------------------------------
  // MESSAGE WRITING CONTROLS
  // Connects draft wording buttons to the suggestion review panel.
  // ---------------------------------------------------------------------------

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
