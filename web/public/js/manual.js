(function () {
  const IN_PLACE_CAMPAIGN_ID = "__in_place__";

  let generatedHtml = "";

  function parseRecipients(raw) {
    if (!raw) return [];
    return raw
      .split(/[,\n]/)
      .map((s) => s.trim())
      .filter((s) => s);
  }

  function parseButtonCaptions(raw) {
    if (!raw) return [];
    return raw
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s);
  }

  function getFormState() {
    const recipients = parseRecipients(document.getElementById("recipients").value);
    const subject = document.getElementById("subject").value.trim();
    const campaignId = document.getElementById("campaign-id").value;
    const captions = parseButtonCaptions(document.getElementById("button-captions").value);
    const confirmChecked = document.getElementById("confirm-recipients").checked;
    return { recipients, subject, campaignId, captions, confirmChecked };
  }

  function canGenerate({ recipients, campaignId, captions, confirmChecked }) {
    if (!recipients.length || !campaignId || !confirmChecked) return false;
    if (campaignId === IN_PLACE_CAMPAIGN_ID) return captions.length > 0;
    return true;
  }

  function updateWarnings() {
    const { recipients, confirmChecked } = getFormState();
    document
      .getElementById("multi-recipient-warning")
      .classList.toggle("hidden", recipients.length <= 1);
    document
      .getElementById("dont-copy-warning")
      .classList.toggle("hidden", !confirmChecked);
  }

  function updateGenerateButton() {
    document.getElementById("generate-btn").disabled = !canGenerate(getFormState());
    updateWarnings();
  }

  function updateInPlaceVisibility() {
    const campaignId = document.getElementById("campaign-id").value;
    const isInPlace = campaignId === IN_PLACE_CAMPAIGN_ID;
    document.getElementById("in-place-group").classList.toggle("hidden", !isInPlace);
    document
      .getElementById("manage-campaigns-link")
      .classList.toggle("hidden", campaignId !== "");
    updateGenerateButton();
  }

  function showFormError(message) {
    const el = document.getElementById("form-error");
    if (!message) {
      el.classList.add("hidden");
      el.textContent = "";
      return;
    }
    el.textContent = message;
    el.classList.remove("hidden");
  }

  function showOutput(html) {
    generatedHtml = html;
    document.getElementById("html-preview").innerHTML = html;
    document.getElementById("html-output").value = html;
    document.getElementById("output-section").classList.remove("hidden");
    document.getElementById("copy-status").classList.add("hidden");
  }

  async function loadCampaigns() {
    const select = document.getElementById("campaign-id");
    const campaigns = await OneClickAPI.get("/api/campaigns");
    while (select.options.length > 2) {
      select.remove(2);
    }
    campaigns.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name;
      select.appendChild(opt);
    });
  }

  async function buildLinkButtons(campaignId, captions) {
    if (campaignId === IN_PLACE_CAMPAIGN_ID) {
      return captions.map((text) => ({ text }));
    }
    const buttons = await OneClickAPI.get(`/api/campaigns/${campaignId}/buttons`);
    if (!buttons.length) {
      throw new Error("This campaign has no response buttons. Add buttons in settings.");
    }
    return buttons.map((b) => ({ response_button_id: b.id }));
  }

  async function copyHtml() {
    const status = document.getElementById("copy-status");
    if (!generatedHtml) return;

    try {
      if (navigator.clipboard.write && window.ClipboardItem) {
        const htmlBlob = new Blob([generatedHtml], { type: "text/html" });
        const textBlob = new Blob([generatedHtml], { type: "text/plain" });
        await navigator.clipboard.write([
          new ClipboardItem({ "text/html": htmlBlob, "text/plain": textBlob }),
        ]);
      } else {
        await navigator.clipboard.writeText(generatedHtml);
      }
      status.textContent = "Copied!";
      status.classList.remove("hidden");
    } catch {
      status.textContent = "Copy failed — select the raw HTML and copy manually.";
      status.classList.remove("hidden");
    }
  }

  document.getElementById("generate-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    showFormError("");

    const { recipients, subject, campaignId, captions } = getFormState();
    if (!canGenerate(getFormState())) return;

    const generateBtn = document.getElementById("generate-btn");
    generateBtn.disabled = true;

    try {
      const linkButtons = await buildLinkButtons(campaignId, captions);
      const result = await OneClickAPI.post("/api/links", {
        subject,
        recipients,
        email_id: crypto.randomUUID(),
        host_url: window.location.origin,
        buttons: linkButtons,
      });
      showOutput(result.html);
    } catch (err) {
      showFormError(err.message || "Failed to generate response block.");
    } finally {
      updateGenerateButton();
    }
  });

  document.getElementById("copy-btn").addEventListener("click", copyHtml);

  ["recipients", "subject", "button-captions"].forEach((id) => {
    document.getElementById(id).addEventListener("input", updateGenerateButton);
  });

  document.getElementById("campaign-id").addEventListener("change", updateInPlaceVisibility);
  document.getElementById("confirm-recipients").addEventListener("change", updateGenerateButton);

  document.getElementById("sign-out-link").addEventListener("click", (e) => {
    e.preventDefault();
    OneClickAuth.signOut();
  });

  OneClickAuth.onAuthChange((user) => {
    document.getElementById("auth-gate").classList.toggle("hidden", !!user);
    document.getElementById("main").classList.toggle("hidden", !user);
    if (user) loadCampaigns();
  });
})();
