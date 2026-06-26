(function () {
  const API_BASE = window.location.origin;

  window.OneClickAPI = {
    async getToken() {
      const auth = window.firebaseAuth;
      if (!auth?.currentUser) return null;
      return auth.currentUser.getIdToken();
    },

    async request(path, options = {}) {
      const token = await this.getToken();
      const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
      if (token) headers.Authorization = `Bearer ${token}`;
      const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
      if (res.status === 204) return null;
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
      return data;
    },

    get: (path) => window.OneClickAPI.request(path),
    post: (path, body) =>
      window.OneClickAPI.request(path, { method: "POST", body: JSON.stringify(body) }),
    put: (path, body) =>
      window.OneClickAPI.request(path, { method: "PUT", body: JSON.stringify(body) }),
    delete: (path) => window.OneClickAPI.request(path, { method: "DELETE" }),
  };

  window.OneClickAuth = {
    onReady(callback) {
      if (window.firebaseAuth) return callback(window.firebaseAuth);
      window.addEventListener("firebase-ready", () => callback(window.firebaseAuth));
    },

    onAuthChange(callback) {
      this.onReady((auth) => auth.onAuthStateChanged(callback));
    },

    async signIn() {
      const { GoogleAuthProvider, signInWithPopup } = await import(
        "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js"
      );
      const provider = new GoogleAuthProvider();
      const result = await signInWithPopup(window.firebaseAuth, provider);
      return result.user;
    },

    async signOut() {
      const { signOut } = await import(
        "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js"
      );
      await signOut(window.firebaseAuth);
    },
  };
})();
