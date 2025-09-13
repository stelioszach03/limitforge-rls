export class LimitforgeClient {
  constructor(baseUrl, apiKey, fetchImpl) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.apiKey = apiKey;
    this.fetch = fetchImpl || fetch;
  }
  async check({ resource, subject, cost = 1 }) {
    const res = await this.fetch(`${this.baseUrl}/v1/check`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": this.apiKey },
      body: JSON.stringify({ resource, subject, cost }),
    });
    // Accept 200 and 429 bodies; throw on other errors
    if (!(res.status === 200 || res.status === 429)) {
      throw new Error(`HTTP ${res.status}`);
    }
    const data = await res.json();
    return data; // includes headers field from server
  }
}

export function limitforgeExpress({ baseUrl, apiKey, mapper, cost = 1 }) {
  const client = new LimitforgeClient(baseUrl, apiKey);
  const defaultMapper = (req) => ({ resource: `${req.method}:${req.path}`, subject: req.headers["x-client-id"] || req.headers["x-api-key"] || "anonymous" });
  const map = mapper || defaultMapper;
  return async function (req, res, next) {
    try {
      const { resource, subject } = map(req);
      const decision = await client.check({ resource, subject, cost });
      const headers = decision.headers || {};
      Object.entries(headers).forEach(([k, v]) => res.setHeader(k, String(v)));
      if (!decision.allowed) return res.status(429).send("rate limited");
      next();
    } catch (e) {
      return res.status(503).send("rate limit service unavailable");
    }
  };
}
