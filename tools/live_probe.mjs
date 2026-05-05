import crypto from "node:crypto";
import fs from "node:fs/promises";
import readline from "node:readline/promises";

const MAIN_BASE_URL = "https://api-gw-toc.zeekrlife.com";
const OLD_BASE_URL = "https://api.zeekrline.com";
const NEW_BASE_URL = "https://snc-tsp-api.zeekrlife.com";

const X_CA_SECRET =
  "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCz09z6e9WOcNq+nUMX8Vq1Xe2EmJxuR3XbtureDCS90dfkok";
const OLD_SECRET_KEY = "e83a60805fa54de9bdfcb0f2d6bca757";
const NEW_APP_SECRET = "890efe3207af95348b95f66b2ee7da04";
const AES_KEY = "a01a6db985a2f5d4";
const AES_IV = "ed446b8b8845013d";
const TO_BE_SIGNED_HEADER = new Set([
  "x-app-id",
  "content-type",
  "x-api-signature-nonce",
  "x-timestamp",
  "x-api-signature-version",
  "x-project-id",
  "authorization",
  "accept-language",
  "x-vin",
  "x-device-id",
  "x-platform",
]);

const SENSITIVE_KEYS = new Set([
  "access_token",
  "accesstoken",
  "authorization",
  "authcode",
  "authCode",
  "clientid",
  "clientId",
  "device_id",
  "deviceid",
  "deviceId",
  "latitude",
  "longitude",
  "mobile",
  "phone",
  "plateno",
  "plateNo",
  "refreshtoken",
  "refreshToken",
  "smscode",
  "smsCode",
  "token",
  "userid",
  "userId",
  "vin",
  "x-client-id",
  "x-device-id",
  "x-device-identifier",
  "x-vin",
]);

const state = {
  deviceId: crypto.randomUUID().toUpperCase(),
  mainToken: "",
  phone: "",
  old: {
    userId: "",
    clientId: "",
    accessToken: "",
    refreshToken: "",
  },
  new: {
    accessToken: "",
    refreshToken: "",
  },
};

function nowMs() {
  return String(Date.now());
}

function mainSign(timestamp, nonce) {
  return [timestamp, nonce, X_CA_SECRET].sort().join("");
}

function sha1Hex(value) {
  return crypto.createHash("sha1").update(value).digest("hex");
}

function md5Base64(value) {
  return crypto.createHash("md5").update(value || "").digest("base64");
}

function hmacBase64(algorithm, key, value) {
  return crypto.createHmac(algorithm, key).update(value).digest("base64");
}

function oldSortedParams(params = {}) {
  const pairs = [];
  for (const key of Object.keys(params).sort()) {
    pairs.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(params[key]))}`);
  }
  return pairs.join("&");
}

function oldSign(method, path, headers, { params, bodyText } = {}) {
  const lines = [
    "application/json;responseformat=3",
    `x-api-signature-nonce:${headers["x-api-signature-nonce"]}`,
    "x-api-signature-version:1.0",
    "",
    oldSortedParams(params),
    md5Base64(bodyText),
    headers["x-timestamp"],
    method.toUpperCase(),
    path,
  ];
  return hmacBase64("sha1", OLD_SECRET_KEY, lines.join("\n"));
}

function encryptVin(vin) {
  const cipher = crypto.createCipheriv(
    "aes-128-cbc",
    Buffer.from(AES_KEY, "utf8"),
    Buffer.from(AES_IV, "utf8"),
  );
  return Buffer.concat([cipher.update(vin, "utf8"), cipher.final()]).toString(
    "base64",
  );
}

function newQueryPart(params = {}) {
  const keys = Object.keys(params).sort();
  if (keys.length === 0) {
    return "";
  }
  return (
    keys
      .map((key) => {
        const raw = String(params[key]);
        const escaped = raw.replaceAll("*", "%2A").replaceAll("%2F", "/").replaceAll("%3F", "?");
        return `${key}=${escaped}`;
      })
      .join("&") + "\n"
  );
}

function newSign(method, path, headers, { params, bodyText } = {}) {
  let contentType = "";
  const signedKeys = Object.keys(headers).sort((a, b) =>
    a.toLowerCase().localeCompare(b.toLowerCase()),
  );
  const headerLines = [];
  for (const key of signedKeys) {
    const lower = key.toLowerCase();
    if (!TO_BE_SIGNED_HEADER.has(lower)) {
      continue;
    }
    let value = headers[key];
    if ((lower === "x-vin" || lower === "authorization") && !value) {
      continue;
    }
    if (lower === "x-vin") {
      value = encryptVin(String(value));
      headers[key] = value;
    }
    if (lower === "content-type") {
      contentType = value;
    }
    headerLines.push(`${lower}:${value}\n`);
  }
  const bodyMd5 =
    contentType.includes("application/json") && bodyText
      ? `${md5Base64(bodyText)}\n`
      : "";
  const canonical = `${headerLines.join("")}${newQueryPart(params)}${bodyMd5}${method.toUpperCase()}\n${path}`;
  return hmacBase64("sha256", NEW_APP_SECRET, canonical);
}

function withParams(baseUrl, path, params = {}) {
  const url = new URL(path, baseUrl);
  for (const [key, value] of Object.entries(params)) {
    url.searchParams.set(key, String(value));
  }
  return url;
}

async function fetchJson(baseUrl, path, { method = "GET", params, body, headers = {} } = {}, makeHeaders) {
  const bodyText = body === undefined ? undefined : JSON.stringify(body);
  const requestHeaders = makeHeaders(method, path, { params, bodyText, headers });
  const response = await fetch(withParams(baseUrl, path, params), {
    method,
    headers: requestHeaders,
    body: bodyText,
  });
  const text = await response.text();
  let payload;
  try {
    payload = JSON.parse(text);
  } catch {
    throw new Error(`HTTP ${response.status}: ${text.slice(0, 200)}`);
  }
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${JSON.stringify(redact(payload)).slice(0, 500)}`);
  }
  return payload;
}

function mainHeaders() {
  const timestamp = nowMs();
  const nonce = String(crypto.randomInt(10_000_000, 100_000_000));
  const headers = {
    "user-agent": `ZeekrLife/4.0.2 (iPhone; iOS 17.4.1; Scale/3.00)${state.deviceId}`,
    "request-original": "zeekr-app",
    "accept-language": "zh-Hans-CN;q=1, en-CN;q=0.9",
    "content-type": "application/json",
    "x_ca_secret": X_CA_SECRET,
    accept: "*/*",
    risktoken: "G4y5f5YrG1BEGxRBBEKF73higM/lOd6e",
    version: "2",
    workspaceid: "prod",
    "x_ca_key": "APP-SIGN-SECRET-KEY",
    app_type: "IOS",
    app_version: "4.0.2",
    phone_model: "iPhone13",
    phone_version: "17.4.1",
    x_gray_code: "gray74",
    x_ca_timestamp: timestamp,
    x_ca_nonce: nonce,
    x_ca_sign: sha1Hex(mainSign(timestamp, nonce)),
    app_code: "toc_ios_zeekrapp",
    device_id: state.deviceId,
  };
  if (state.mainToken) {
    headers.authorization = state.mainToken;
  }
  return headers;
}

function oldHeaders(method, path, { params, bodyText, headers: extraHeaders }) {
  const headers = {
    "x-timestamp": nowMs(),
    "x-api-signature-nonce": crypto.randomUUID().toUpperCase(),
    "content-type": "application/json",
    "x-api-signature-version": "1.0",
    "x-app-id": "ZEEKRAPP",
    "user-agent": "ZeekrLife/4.0.2 (iPhone; iOS 17.4.1; Scale/3.00)",
    "x-device-model": "iPhone",
    "x-device-manufacture": "Apple",
    "x-agent-type": "iOS",
    "x-device-type": "mobile",
    platform: "NON-CMA",
    "x-env-type": "production",
    "accept-language": "zh-Hans-CN;q=1, en-CN;q=0.9",
    "x-agent-version": "17.4.1",
    accept: "application/json;responseformat=3",
    "x-device-brand": "Apple",
    "x-operator-code": "ZEEKR",
    "x-device-identifier": state.deviceId,
    ...extraHeaders,
  };
  headers["x-signature"] = oldSign(method, path, headers, { params, bodyText });
  if (state.old.accessToken) {
    headers.authorization = state.old.accessToken;
  }
  if (state.old.clientId) {
    headers["x-client-id"] = state.old.clientId;
  }
  return headers;
}

function newHeaders(method, path, { params, bodyText, headers: extraHeaders }) {
  const headers = {
    "X-APP-ID": "ZEEKRCNCH001M0000",
    "X-TIMESTAMP": nowMs(),
    "X-API-SIGNATURE-VERSION": "2.0",
    "X-SIGNATURE": "",
    "Accept-Language": "zh-CN",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json;charset=UTF-8",
    "X-PROJECT-ID": "ZEEKR",
    "X-P": "iOS",
    "X-DEVICE-ID": state.deviceId,
    "X-APP-OS-VERSION": "4.9.9",
    "X-PLATFORM": "APP",
    "X-API-SIGNATURE-NONCE": crypto.randomUUID().toUpperCase(),
    "User-Agent": "ZeekrLife/2025061706 CFNetwork/3826.500.131 Darwin/24.5.0",
    ...extraHeaders,
  };
  if (state.new.accessToken && !headers.Authorization) {
    headers.Authorization = state.new.accessToken;
  }
  headers["X-SIGNATURE"] = newSign(method, path, headers, { params, bodyText });
  return headers;
}

async function mainFetch(path, options = {}) {
  const payload = await fetchJson(
    MAIN_BASE_URL,
    path,
    options,
    () => mainHeaders(),
  );
  if (String(payload.code) !== "000000") {
    throw new Error(`Main API ${payload.code}: ${payload.msg}`);
  }
  return payload.data;
}

async function oldFetch(path, options = {}) {
  const payload = await fetchJson(OLD_BASE_URL, path, options, oldHeaders);
  if (String(payload.code) !== "1000") {
    throw new Error(`Old API ${payload.code}: ${payload.message}`);
  }
  return payload.data;
}

async function newFetch(path, options = {}) {
  const payload = await fetchJson(NEW_BASE_URL, path, options, newHeaders);
  if (String(payload.code) !== "000000") {
    throw new Error(`New API ${payload.code}: ${payload.msg}`);
  }
  return payload.data;
}

function redact(value) {
  if (Array.isArray(value)) {
    return value.map(redact);
  }
  if (value && typeof value === "object") {
    const result = {};
    for (const [key, item] of Object.entries(value)) {
      if (SENSITIVE_KEYS.has(key) || SENSITIVE_KEYS.has(key.toLowerCase())) {
        result[key] = "***";
      } else {
        result[key] = redact(item);
      }
    }
    return result;
  }
  return value;
}

function collectPaths(value, prefix = "", paths = {}) {
  if (Array.isArray(value)) {
    paths[prefix || "$"] = `array(${value.length})`;
    if (value.length > 0) {
      collectPaths(value[0], `${prefix}[]`, paths);
    }
    return paths;
  }
  if (value && typeof value === "object") {
    paths[prefix || "$"] = "object";
    for (const [key, item] of Object.entries(value)) {
      collectPaths(item, prefix ? `${prefix}.${key}` : key, paths);
    }
    return paths;
  }
  paths[prefix || "$"] = value === null ? "null" : typeof value;
  return paths;
}

function shortId(value) {
  if (!value || typeof value !== "string") {
    return "***";
  }
  return `***${value.slice(-4)}`;
}

async function askCode(rl) {
  const answer = await rl.question("SMS code (input stays local): ");
  return answer.trim();
}

async function main() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  try {
    state.phone = (await rl.question("China mobile number (+86, digits only): ")).trim();
    if (!state.phone) {
      throw new Error("Mobile number is required.");
    }

    console.log("Sending SMS code...");
    await mainFetch("/zeekrlife-app-user/v1/user/pub/sms/authCode", {
      method: "GET",
      params: {
        mobile: state.phone,
        regionCode: "+86",
        x_ca_time: nowMs(),
      },
    });

    const smsCode = await askCode(rl);
    if (!smsCode) {
      throw new Error("SMS code is required.");
    }

    console.log("Logging in...");
    const login = await mainFetch("/zeekrlife-app-user/v1/user/pub/login/mobile", {
      method: "POST",
      body: {
        mobile: state.phone,
        deviceId: state.deviceId,
        smsCode,
        channel: 2,
        x_ca_time: nowMs(),
        deviceName: "iPhone13",
        skipSmsCode: "0",
        regionCode: "+86",
        ip: "192.168.1.1",
      },
    });
    state.mainToken = login.jwtToken;

    console.log("Authorizing vehicle APIs...");
    const authCodes = await mainFetch("/zeekrlife-mp-auth2/v1/auth/accessCodeList", {
      method: "GET",
      params: { envType: 3 },
    });
    const oldAuth = await oldFetch("/auth/account/session/secure", {
      method: "POST",
      params: { identity_type: "zeekr" },
      body: { authCode: authCodes.YIKAT_NEW },
    });
    state.old.userId = oldAuth.userId;
    state.old.clientId = oldAuth.clientId;
    state.old.accessToken = oldAuth.accessToken;
    state.old.refreshToken = oldAuth.refreshToken;

    const newAuth = await newFetch("/ms-user-auth/v1.0/auth/login", {
      method: "POST",
      body: {
        loginDeviceType: 1,
        identityType: 5,
        loginSystem: "ios",
        loginDeviceId: state.deviceId,
        token: state.mainToken,
        loginPhoneBrand: "Apple",
      },
    });
    state.new.accessToken = newAuth.accessToken;
    state.new.refreshToken = newAuth.refreshToken;

    console.log("Fetching vehicles...");
    const allVehicles = await newFetch("/ms-app-bff/api/v3.0/veh/vehicle-list", {
      method: "GET",
      params: { needSharedCar: "true" },
      headers: { Authorization: state.mainToken },
    });
    const oldVehiclesPayload = await oldFetch("/device-platform/user/vehicle/secure", {
      method: "GET",
      params: {
        id: state.old.userId,
        needSharedCar: 1,
      },
    });
    const oldVins = new Set((oldVehiclesPayload?.list || []).map((item) => item.vin));

    const vehicleSummaries = [];
    const statuses = {};
    for (const vehicle of allVehicles || []) {
      const vin = vehicle.vin;
      const isOld = oldVins.has(vin);
      console.log(`Fetching status for ${shortId(vin)} (${isOld ? "old" : "new"} API)...`);
      let status;
      if (isOld) {
        const data = await oldFetch(`/remote-control/vehicle/status/${vin}`, {
          method: "GET",
          params: {
            latest: "Local",
            target: encodeURIComponent("basic,more"),
            userId: state.old.userId,
          },
        });
        status = data?.vehicleStatus || {};
      } else {
        status = await newFetch("/ms-vehicle-status/api/v1.0/vehicle/status/latest", {
          method: "GET",
          params: { latest: "false", target: "new" },
          headers: {
            "X-VIN": vin,
            "X-APP-ID": "ZEEKRCNCH001M0001",
          },
        });
      }
      statuses[shortId(vin)] = {
        isOld,
        redactedStatus: redact(status),
        fieldInventory: collectPaths(status),
      };
      vehicleSummaries.push({
        vin: shortId(vin),
        plateNo: shortId(vehicle.plateNo),
        model: vehicle.appModelCode,
        osVersion: vehicle.displayOSVersion,
        isOld,
      });
    }

    const result = {
      generatedAt: new Date().toISOString(),
      vehicleCount: (allVehicles || []).length,
      vehicles: vehicleSummaries,
      statusByVehicle: statuses,
    };
    await fs.writeFile("live_probe_result.redacted.json", JSON.stringify(result, null, 2));

    console.log("");
    console.log(`Done. Vehicles: ${result.vehicleCount}`);
    console.log("Redacted result written to live_probe_result.redacted.json");
  } finally {
    rl.close();
  }
}

main().catch(async (error) => {
  await fs.writeFile(
    "live_probe_error.redacted.txt",
    `${new Date().toISOString()}\n${error.stack || error.message}\n`,
  );
  console.error("");
  console.error(`Probe failed: ${error.message}`);
  console.error("Redacted error written to live_probe_error.redacted.txt");
  process.exitCode = 1;
});
