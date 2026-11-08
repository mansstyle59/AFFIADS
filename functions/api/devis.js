const MAX_REQUEST_BYTES = 16 * 1024;
const TURNSTILE_TOKEN_MAX_LENGTH = 2048;

const MAX_LENGTHS = {
  name: 100,
  email: 254,
  company: 120,
  projectType: 80,
  budget: 50,
  message: 4000
};

const PROJECT_TYPES = new Set([
  "Site vitrine essentiel",
  "Site vitrine avancé",
  "Outil numérique",
  "Application web",
  "Automatisation IA",
  "Autre / à définir"
]);

const BUDGETS = new Set([
  "À définir",
  "Moins de 1 000 €",
  "1 000 à 3 000 €",
  "3 000 à 6 000 €",
  "Plus de 6 000 €"
]);

function jsonResponse(payload, status) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store"
    }
  });
}

async function readJsonBody(request) {
  const contentLength = request.headers.get("content-length");
  if (contentLength !== null) {
    const length = Number(contentLength);
    if (!Number.isSafeInteger(length) || length < 0) {
      throw new Error("INVALID_CONTENT_LENGTH");
    }
    if (length > MAX_REQUEST_BYTES) {
      throw new Error("BODY_TOO_LARGE");
    }
  }

  if (!request.body) throw new Error("EMPTY_BODY");

  const reader = request.body.getReader();
  const chunks = [];
  let totalBytes = 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    totalBytes += value.byteLength;
    if (totalBytes > MAX_REQUEST_BYTES) {
      try { await reader.cancel(); } catch { /* Le flux est déjà interrompu. */ }
      throw new Error("BODY_TOO_LARGE");
    }
    chunks.push(value);
  }

  const body = new Uint8Array(totalBytes);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }

  return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(body));
}

// Les champs repris dans les en-têtes ou les valeurs de formulaire doivent rester sur une ligne.
function cleanSingleLine(value, maxLength) {
  if (typeof value !== "string") return "";
  return value
    .replace(/[\u0000-\u001F\u007F-\u009F\u2028\u2029]/g, "")
    .trim()
    .slice(0, maxLength);
}

// Le message peut conserver ses retours à la ligne, mais pas les caractères de contrôle invisibles.
function cleanMessage(value, maxLength) {
  if (typeof value !== "string") return "";
  return value
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/g, "")
    .trim()
    .slice(0, maxLength);
}

function validEmail(email) {
  return email.length <= MAX_LENGTHS.email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

async function verifyTurnstile(token, secret, expectedHostname) {
  if (!token || token.length > TURNSTILE_TOKEN_MAX_LENGTH || !expectedHostname) {
    return { valid: false, unavailable: false };
  }

  try {
    const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ secret, response: token })
    });

    if (!response.ok) return { valid: false, unavailable: true };
    const result = await response.json();
    const hostnameMatches = typeof result.hostname === "string"
      && result.hostname.toLowerCase().replace(/\.$/, "") === expectedHostname;

    return {
      valid: result.success === true && result.action === "quote" && hostnameMatches,
      unavailable: false
    };
  } catch {
    return { valid: false, unavailable: true };
  }
}

export async function onRequestPost({ request, env }) {
  const contentType = request.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return jsonResponse({ ok: false, message: "Format de demande non pris en charge." }, 415);
  }

  let data;
  try {
    data = await readJsonBody(request);
  } catch (error) {
    if (error && error.message === "BODY_TOO_LARGE") {
      return jsonResponse({ ok: false, message: "La demande est trop volumineuse." }, 413);
    }
    return jsonResponse({ ok: false, message: "La demande reçue est invalide." }, 400);
  }

  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return jsonResponse({ ok: false, message: "La demande reçue est invalide." }, 400);
  }

  // Honeypot anti-spam : répondre discrètement sans envoyer de message.
  if (cleanSingleLine(data.website, 200)) {
    return jsonResponse({ ok: true }, 200);
  }

  const name = cleanSingleLine(data.name, MAX_LENGTHS.name);
  const email = cleanSingleLine(data.email, MAX_LENGTHS.email);
  const company = cleanSingleLine(data.company, MAX_LENGTHS.company);
  const projectType = cleanSingleLine(data.projectType, MAX_LENGTHS.projectType);
  const budget = cleanSingleLine(data.budget, MAX_LENGTHS.budget);
  const message = cleanMessage(data.message, MAX_LENGTHS.message);

  if (!name || !validEmail(email) || !PROJECT_TYPES.has(projectType) || !BUDGETS.has(budget) || message.length < 10) {
    return jsonResponse({ ok: false, message: "Vérifiez les champs obligatoires puis réessayez." }, 400);
  }

  const turnstileSecret = env.TURNSTILE_SECRET_KEY;
  if (!turnstileSecret) {
    return jsonResponse({ ok: false, message: "La protection anti-spam n’est pas encore configurée." }, 503);
  }

  const expectedHostname = cleanSingleLine(env.TURNSTILE_EXPECTED_HOSTNAME, 253)
    .toLowerCase()
    .replace(/\.$/, "");

  // Sans hostname de production explicite, ne jamais accepter une vérification Turnstile.
  if (!expectedHostname || !/^[a-z0-9.-]+$/.test(expectedHostname)) {
    return jsonResponse({
      ok: false,
      message: "Le hostname de vérification anti-spam n’est pas configuré."
    }, 503);
  }

  const turnstileToken = cleanSingleLine(data["cf-turnstile-response"], TURNSTILE_TOKEN_MAX_LENGTH);
  const turnstile = await verifyTurnstile(
    turnstileToken,
    turnstileSecret,
    expectedHostname
  );

  if (turnstile.unavailable) {
    return jsonResponse({
      ok: false,
      message: "La vérification anti-spam est momentanément indisponible. Réessayez plus tard."
    }, 503);
  }
  if (!turnstile.valid) {
    return jsonResponse({
      ok: false,
      message: "Veuillez valider la vérification anti-spam puis réessayer."
    }, 400);
  }

  const apiKey = env.RESEND_API_KEY;
  const recipient = env.QUOTE_TO_EMAIL;
  const sender = env.QUOTE_FROM_EMAIL;

  if (!apiKey || !recipient || !sender) {
    return jsonResponse({
      ok: false,
      message: "Le formulaire de devis n’est pas encore configuré. Merci de réessayer ultérieurement."
    }, 503);
  }

  const emailText = [
    "Nouvelle demande de devis AFFIADS",
    "",
    "Nom : " + name,
    "E-mail : " + email,
    "Entreprise : " + (company || "Non renseignée"),
    "Projet : " + projectType,
    "Budget : " + budget,
    "",
    "Message :",
    message
  ].join("\n");

  let mailResponse;
  try {
    mailResponse = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + apiKey,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        from: sender,
        to: [recipient],
        reply_to: email,
        subject: "Nouvelle demande de devis AFFIADS — " + name,
        text: emailText
      })
    });
  } catch {
    return jsonResponse({ ok: false, message: "Le service d’envoi est momentanément indisponible." }, 502);
  }

  if (!mailResponse.ok) {
    // Ne pas exposer les détails du fournisseur ou les secrets côté client.
    return jsonResponse({ ok: false, message: "L’envoi a échoué. Veuillez réessayer plus tard." }, 502);
  }

  return jsonResponse({ ok: true }, 200);
}