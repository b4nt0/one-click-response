(function () {
  let currentCampaignId = null;

  function showView(view) {
    ["list-view", "detail-view", "create-view"].forEach((id) => {
      document.getElementById(id).classList.toggle("hidden", id !== view);
    });
  }

  async function loadCampaigns() {
    const campaigns = await OneClickAPI.get("/api/campaigns");
    const list = document.getElementById("campaigns-list");
    if (!campaigns.length) {
      list.innerHTML = '<p class="muted">No campaigns yet. Create one to get started.</p>';
      return;
    }
    list.innerHTML = campaigns
      .map(
        (c) => `
      <div class="list-item">
        <span>${escapeHtml(c.name)}</span>
        <button class="btn btn-secondary" data-id="${c.id}">Edit</button>
      </div>`
      )
      .join("");
    list.querySelectorAll("button[data-id]").forEach((btn) => {
      btn.addEventListener("click", () => openCampaign(btn.dataset.id));
    });
  }

  async function openCampaign(id) {
    currentCampaignId = id;
    const campaign = await OneClickAPI.get(`/api/campaigns/${id}`);
    document.getElementById("detail-title").textContent = campaign.name;
    document.getElementById("campaign-name").value = campaign.name;
    document.getElementById("record-answers").checked = campaign.record_answers;
    document.getElementById("forward-answers").checked = campaign.forward_answers;
    await loadButtons(id);
    if (campaign.record_answers) {
      await loadResponses(id);
      document.getElementById("responses-section").classList.remove("hidden");
    } else {
      document.getElementById("responses-section").classList.add("hidden");
    }
    showView("detail-view");
  }

  async function loadButtons(campaignId) {
    const buttons = await OneClickAPI.get(`/api/campaigns/${campaignId}/buttons`);
    const list = document.getElementById("buttons-list");
    if (!buttons.length) {
      list.innerHTML = '<p class="muted">No buttons yet.</p>';
      return;
    }
    list.innerHTML = buttons
      .map(
        (b) => `
      <div class="list-item">
        <span>${escapeHtml(b.text)}</span>
        <button class="btn btn-danger btn-sm" data-delete="${b.id}">Delete</button>
      </div>`
      )
      .join("");
    list.querySelectorAll("[data-delete]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this button?")) return;
        await OneClickAPI.delete(`/api/buttons/${btn.dataset.delete}`);
        await loadButtons(currentCampaignId);
      });
    });
  }

  async function loadResponses(campaignId) {
    const responses = await OneClickAPI.get(`/api/campaigns/${campaignId}/responses`);
    const tbody = document.getElementById("responses-table");
    tbody.innerHTML = responses
      .map(
        (r) => `
      <tr>
        <td>${escapeHtml(r.text)}</td>
        <td>${escapeHtml(r.recipient)}</td>
        <td>${escapeHtml(r.subject)}</td>
        <td>${new Date(r.created_at).toLocaleString()}</td>
      </tr>`
      )
      .join("");
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  document.getElementById("new-campaign-btn").addEventListener("click", () => showView("create-view"));
  document.getElementById("back-btn").addEventListener("click", () => {
    currentCampaignId = null;
    showView("list-view");
    loadCampaigns();
  });
  document.getElementById("create-back-btn").addEventListener("click", () => showView("list-view"));

  document.getElementById("create-campaign-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const campaign = await OneClickAPI.post("/api/campaigns", {
      name: document.getElementById("new-campaign-name").value,
      record_answers: document.getElementById("new-record-answers").checked,
      forward_answers: document.getElementById("new-forward-answers").checked,
    });
    document.getElementById("create-campaign-form").reset();
    await openCampaign(campaign.id);
  });

  document.getElementById("campaign-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    await OneClickAPI.put(`/api/campaigns/${currentCampaignId}`, {
      name: document.getElementById("campaign-name").value,
      record_answers: document.getElementById("record-answers").checked,
      forward_answers: document.getElementById("forward-answers").checked,
    });
    const record = document.getElementById("record-answers").checked;
    document.getElementById("responses-section").classList.toggle("hidden", !record);
    if (record) await loadResponses(currentCampaignId);
  });

  document.getElementById("delete-campaign-btn").addEventListener("click", async () => {
    if (!confirm("Delete this campaign and all its buttons?")) return;
    await OneClickAPI.delete(`/api/campaigns/${currentCampaignId}`);
    currentCampaignId = null;
    showView("list-view");
    loadCampaigns();
  });

  document.getElementById("add-button-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = document.getElementById("new-button-text").value;
    await OneClickAPI.post(`/api/campaigns/${currentCampaignId}/buttons`, { text });
    document.getElementById("new-button-text").value = "";
    await loadButtons(currentCampaignId);
  });

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
