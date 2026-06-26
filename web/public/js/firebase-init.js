(function () {
  const config = window.FIREBASE_CONFIG;

  if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
    import("https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js").then(({ initializeApp }) => {
      import("https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js").then(({ getAuth, connectAuthEmulator }) => {
        const app = initializeApp(config);
        const auth = getAuth(app);
        connectAuthEmulator(auth, "http://127.0.0.1:9099", { disableWarnings: true });
        window.firebaseApp = app;
        window.firebaseAuth = auth;
        window.dispatchEvent(new Event("firebase-ready"));
      });
    });
  } else {
    import("https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js").then(({ initializeApp }) => {
      import("https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js").then(({ getAuth }) => {
        const app = initializeApp(config);
        const auth = getAuth(app);
        window.firebaseApp = app;
        window.firebaseAuth = auth;
        window.dispatchEvent(new Event("firebase-ready"));
      });
    });
  }
})();
