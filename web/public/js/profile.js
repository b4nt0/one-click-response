(function () {
  document.getElementById("rotate-key-btn").addEventListener("click", async () => {
    if (
      !confirm(
        "Rotate your encryption key? This will invalidate all response buttons in unsent emails."
      )
    ) {
      return;
    }
    const btn = document.getElementById("rotate-key-btn");
    btn.disabled = true;
    try {
      const result = await OneClickAPI.post("/api/users/rotate-key", {});
      const status = document.getElementById("rotate-status");
      status.textContent = result.message || "Key rotated successfully.";
      status.classList.remove("hidden");
    } catch (err) {
      alert(err.message);
    } finally {
      btn.disabled = false;
    }
  });

  document.getElementById("sign-out-link").addEventListener("click", (e) => {
    e.preventDefault();
    OneClickAuth.signOut();
  });

  OneClickAuth.onAuthChange((user) => {
    document.getElementById("auth-gate").classList.toggle("hidden", !!user);
    document.getElementById("main").classList.toggle("hidden", !user);
    if (user) document.getElementById("user-email").textContent = user.email;
  });
})();
