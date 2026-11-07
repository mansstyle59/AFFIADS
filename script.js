(() => {
  "use strict";

  const menuButton = document.querySelector(".menu-toggle");
  const navigation = document.querySelector("#navigation");
  const form = document.querySelector("#quote-form");
  const status = document.querySelector("#form-status");
  const year = document.querySelector("#year");

  if (year) year.textContent = String(new Date().getFullYear());

  if (menuButton && navigation) {
    menuButton.addEventListener("click", () => {
      const isOpen = menuButton.getAttribute("aria-expanded") === "true";
      menuButton.setAttribute("aria-expanded", String(!isOpen));
      menuButton.setAttribute("aria-label", isOpen ? "Ouvrir le menu" : "Fermer le menu");
      navigation.classList.toggle("is-open", !isOpen);
    });

    navigation.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        menuButton.setAttribute("aria-expanded", "false");
        menuButton.setAttribute("aria-label", "Ouvrir le menu");
        navigation.classList.remove("is-open");
      });
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && navigation.classList.contains("is-open")) {
        menuButton.setAttribute("aria-expanded", "false");
        menuButton.setAttribute("aria-label", "Ouvrir le menu");
        navigation.classList.remove("is-open");
        menuButton.focus();
      }
    });
  }

  if (!form || !status) return;

  const setStatus = (message, state) => {
    status.textContent = message;
    status.dataset.state = state;
  };

  const submitButton = form.querySelector('button[type="submit"]');
  const turnstileElement = form.querySelector("#turnstile-widget");
  const turnstileStatus = form.querySelector("#turnstile-status");
  const siteKey = turnstileElement?.dataset.sitekey?.trim();
  const turnstileConfigured = Boolean(siteKey && siteKey !== "YOUR_TURNSTILE_SITE_KEY");
  let turnstileWidgetId = null;

  // Éviter une soumission vouée à l’échec tant que la clé publique n’est pas configurée.
  if (!turnstileConfigured) {
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.dataset.disabledReason = "setup";
    }
    setStatus(
      "Le formulaire de devis sera activé après la configuration de la vérification anti-spam.",
      "error"
    );
  }
  let turnstileLoadFailed = false;

  const setTurnstileStatus = (message, state = "") => {
    if (!turnstileStatus) return;
    turnstileStatus.textContent = message;
    turnstileStatus.dataset.state = state;
  };

  if (turnstileConfigured) {
    const turnstileScript = document.createElement("script");
    turnstileScript.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
    turnstileScript.async = true;
    turnstileScript.defer = true;
    turnstileScript.onload = () => {
      if (!window.turnstile) {
        turnstileLoadFailed = true;
        setTurnstileStatus("La vérification anti-spam n’a pas pu charger. Rechargez la page.", "error");
        return;
      }

      try {
        turnstileWidgetId = window.turnstile.render(turnstileElement, {
          sitekey: siteKey,
          action: "quote",
          size: "flexible",
          callback: () => setTurnstileStatus("", ""),
          "expired-callback": () => setTurnstileStatus("La vérification a expiré. Recommencez.", "error"),
          "error-callback": () => {
            turnstileLoadFailed = true;
            setTurnstileStatus("La vérification est indisponible. Rechargez la page ou réessayez.", "error");
          }
        });
      } catch {
        turnstileLoadFailed = true;
        setTurnstileStatus("La vérification anti-spam n’a pas pu démarrer. Rechargez la page.", "error");
      }
    };
    turnstileScript.onerror = () => {
      turnstileLoadFailed = true;
      setTurnstileStatus("La vérification anti-spam n’a pas pu charger. Rechargez la page.", "error");
    };
    document.head.appendChild(turnstileScript);
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!form.reportValidity()) return;

    const originalButtonText = submitButton ? submitButton.innerHTML : "";
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());

    if (turnstileConfigured && !payload["cf-turnstile-response"]) {
      setStatus(
        turnstileLoadFailed
          ? "La vérification anti-spam n’est pas disponible. Rechargez la page puis réessayez."
          : "Veuillez valider la vérification anti-spam avant d’envoyer votre demande.",
        "error"
      );
      return;
    }

    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "Envoi en cours…";
    }
    setStatus("", "");

    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify(payload)
      });

      const result = await response.json().catch(() => ({}));

      if (!response.ok || !result.ok) {
        throw new Error(result.message || "L’envoi n’a pas pu aboutir. Réessayez un peu plus tard.");
      }

      form.reset();
      setStatus("Merci ! Votre demande a bien été envoyée. AFFIADS reviendra vers vous.", "success");
    } catch (error) {
      const message = error && error.message
        ? error.message
        : "Une erreur est survenue. Veuillez réessayer plus tard.";
      setStatus(message, "error");
    } finally {
      if (turnstileConfigured && turnstileWidgetId !== null && window.turnstile) {
        try { window.turnstile.reset(turnstileWidgetId); } catch { /* Le widget peut déjà être réinitialisé. */ }
      }
      if (submitButton) {
        submitButton.disabled = !turnstileConfigured;
        submitButton.innerHTML = originalButtonText;
      }
    }
  });
})();