const MAX_REQUEST_BYTES = 16 * 1024;
const RATE_LIMIT_RETRY_SECONDS = 60;

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

function jsonResponse(payload, status, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      ...extraHeaders
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

async function enforceQuoteRateLimit(request, env) {
  const limiter = env && env.QUOTE_RATE_LIMITER;
  const clientIp = request.headers.get("cf-connecting-ip");

  // Cloudflare injecte cette adresse sur les requêtes proxifiées. Ne pas contourner
  // le limiteur si le binding ou l'identifiant client manque : refuser temporairement.
  if (!limiter || typeof limiter.limit !== "function" || !clientIp) {
    return { allowed: false, unavailable: true };
  }

  try {
    const { success } = await limiter.limit({ key: "quote:" + clientIp });
    return { allowed: success === true, unavailable: false };
  } catch {
    return { allowed: false, unavailable: true };
  }
}

export async function onRequestPost({ request, env }) {
  const contentType = request.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return jsonResponse({ ok: false, message: "Format de demande non pris en charge." }, 415);
  }

  const rateLimit = await enforceQuoteRateLimit(request, env);
  if (rateLimit.unavailable) {
    return jsonResponse({
      ok: false,
      message: "Le formulaire est temporairement indisponible. Merci de réessayer ultérieurement."
    }, 503);
  }
  if (!rateLimit.allowed) {
    return jsonResponse({
      ok: false,
      message: "Trop de demandes depuis votre réseau. Veuillez réessayer dans une minute."
    }, 429, { "retry-after": String(RATE_LIMIT_RETRY_SECONDS) });
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