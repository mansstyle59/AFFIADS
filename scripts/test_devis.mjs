import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

// Charge le handler Cloudflare Pages dans un wrapper de test sans dépendance externe.
const source = await readFile(new URL("../functions/api/devis.js", import.meta.url), "utf8");
const loadHandler = new Function(
  source.replace("export async function onRequestPost", "async function onRequestPost")
    + "\nreturn onRequestPost;"
);
const onRequestPost = loadHandler();

const payload = {
  name: "Test AFFIADS",
  email: "test@example.fr",
  company: "",
  projectType: "Site vitrine essentiel",
  budget: "À définir",
  message: "Demande de test automatisé du formulaire AFFIADS.",
  "cf-turnstile-response": "token-test"
};

function makeRequest(contentType = "application/json") {
  return new Request("https://affiads.pages.dev/api/devis", {
    method: "POST",
    headers: { "content-type": contentType },
    body: JSON.stringify(payload)
  });
}

async function callHandler(env, contentType) {
  return onRequestPost({ request: makeRequest(contentType), env });
}

const originalFetch = globalThis.fetch;
try {
  // 0) Refuser les faux media types JSON tout en acceptant les paramètres MIME.
  let fetchCalls = 0;
  globalThis.fetch = async () => {
    fetchCalls += 1;
    throw new Error("fetch should not be called for unsupported media types");
  };
  const jsonp = await callHandler({}, "application/jsonp");
  assert.equal(jsonp.status, 415);
  const nestedJson = await callHandler({}, "text/application/json");
  assert.equal(nestedJson.status, 415);
  const jsonWithCharset = await callHandler({ TURNSTILE_SECRET_KEY: "test-secret" }, "application/json; charset=utf-8");
  assert.equal(jsonWithCharset.status, 503); // Le type MIME est accepté, puis la config hostname manque.
  assert.equal(fetchCalls, 0);
  console.log("OK — Content-Type strict : faux media types rejetés, charset JSON accepté");

  // 1) Configuration hostname absente : refus immédiat, aucun appel externe.
  fetchCalls = 0;
  globalThis.fetch = async () => {
    fetchCalls += 1;
    throw new Error("fetch should not be called when hostname config is missing");
  };
  const missingHostname = await callHandler({
    TURNSTILE_SECRET_KEY: "test-secret",
    RESEND_API_KEY: "test-resend",
    QUOTE_TO_EMAIL: "owner@example.fr",
    QUOTE_FROM_EMAIL: "AFFIADS <contact@example.fr>"
  });
  assert.equal(missingHostname.status, 503);
  assert.equal(fetchCalls, 0);
  console.log("OK — hostname Turnstile absent : échec fermé avant appel externe");

  // 2) Hostname Turnstile différent : refus, aucun e-mail Resend.
  fetchCalls = 0;
  globalThis.fetch = async (url) => {
    fetchCalls += 1;
    assert.match(String(url), /siteverify/);
    return new Response(JSON.stringify({
      success: true,
      action: "quote",
      hostname: "untrusted.example"
    }), { status: 200, headers: { "content-type": "application/json" } });
  };
  const mismatch = await callHandler({
    TURNSTILE_SECRET_KEY: "test-secret",
    TURNSTILE_EXPECTED_HOSTNAME: "affiads.pages.dev",
    RESEND_API_KEY: "test-resend",
    QUOTE_TO_EMAIL: "owner@example.fr",
    QUOTE_FROM_EMAIL: "AFFIADS <contact@example.fr>"
  });
  assert.equal(mismatch.status, 400);
  assert.equal(fetchCalls, 1);
  console.log("OK — hostname Turnstile incorrect : aucun envoi e-mail");

  // 3) Hostname correct : comparaison normalisée et notification simulée.
  fetchCalls = 0;
  globalThis.fetch = async (url) => {
    fetchCalls += 1;
    if (String(url).includes("siteverify")) {
      return new Response(JSON.stringify({
        success: true,
        action: "quote",
        hostname: "affiads.pages.dev"
      }), { status: 200, headers: { "content-type": "application/json" } });
    }
    assert.match(String(url), /api\.resend\.com\/emails/);
    return new Response(JSON.stringify({ id: "test-email-id" }), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  };
  const valid = await callHandler({
    TURNSTILE_SECRET_KEY: "test-secret",
    TURNSTILE_EXPECTED_HOSTNAME: "AFFIADS.PAGES.DEV.",
    RESEND_API_KEY: "test-resend",
    QUOTE_TO_EMAIL: "owner@example.fr",
    QUOTE_FROM_EMAIL: "AFFIADS <contact@example.fr>"
  });
  assert.equal(valid.status, 200);
  assert.deepEqual(await valid.json(), { ok: true });
  assert.equal(fetchCalls, 2);
  console.log("OK — hostname valide : validation Turnstile puis notification simulée");
} finally {
  globalThis.fetch = originalFetch;
}
