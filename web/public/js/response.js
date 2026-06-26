(function () {
  const API_BASE = window.location.origin;

  function getToken() {
    const params = new URLSearchParams(window.location.search);
    return params.get("p") || "";
  }

  function show(id) {
    ["loading", "confirm-view", "success-view", "duplicate-view", "error-view"].forEach((view) => {
      document.getElementById(view).classList.toggle("hidden", view !== id);
    });
  }

  async function apiPost(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.error || "Request failed");
      err.code = data.code;
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  function buildMailto(ownerEmail, buttonText, subject, campaignName) {
    const campaignPart = campaignName ? `Campaign: ${campaignName}\n` : "";
    const body = `My response: ${buttonText}\n${campaignPart}Re: ${subject}`;
    const params = new URLSearchParams({
      subject: `Re: ${subject}`,
      body,
    });
    return `mailto:${encodeURIComponent(ownerEmail)}?${params.toString()}`;
  }

  let previewData = null;
  const token = getToken();

  async function init() {
    if (!token) {
      show("error-view");
      document.getElementById("error-message").textContent = "Invalid response link.";
      return;
    }

    try {
      previewData = await apiPost("/api/responses/preview", { p: token });
      document.getElementById("button-text").textContent = previewData.button_text;
      document.getElementById("subject-line").textContent = `Re: ${previewData.subject}`;
      if (previewData.campaign_name) {
        document.getElementById("campaign-line").textContent =
          `Campaign: ${previewData.campaign_name}`;
        document.getElementById("campaign-line").classList.remove("hidden");
      }
      show("confirm-view");
    } catch (err) {
      show("error-view");
      document.getElementById("error-message").textContent =
        err.message || "Could not load response details.";
    }
  }

  document.getElementById("confirm-btn").addEventListener("click", async () => {
    const btn = document.getElementById("confirm-btn");
    btn.disabled = true;
    btn.textContent = "Submitting…";

    try {
      await apiPost("/api/responses", { p: token, confirmed: true });
      show("success-view");
      setTimeout(() => window.close(), 8000);
    } catch (err) {
      if (err.code === "duplicate" || err.status === 409) {
        show("duplicate-view");
      } else {
        show("error-view");
        document.getElementById("error-message").textContent =
          err.message || "There was an error registering your response.";
        if (previewData) {
          document.getElementById("mailto-link").href = buildMailto(
            err.data?.owner_email || "",
            previewData.button_text,
            previewData.subject,
            previewData.campaign_name
          );
        }
      }
    }
  });

  init();
})();
