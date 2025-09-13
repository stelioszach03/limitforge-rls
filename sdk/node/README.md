# Limitforge Node SDK

Lightweight client and Express middleware for Limitforge RLS.

Install:
```bash
npm install limitforge-sdk
```

Client usage:
```js
import { LimitforgeClient } from 'limitforge-sdk';

const client = new LimitforgeClient('http://localhost:8000', '<raw-api-key>');
const decision = await client.check({ resource: 'GET:/demo', subject: 'user:1', cost: 1 });
console.log(decision.allowed, decision.headers);
```

Express middleware:
```js
import express from 'express';
import { limitforgeExpress } from 'limitforge-sdk/middleware-express.js';

const app = express();
app.use(limitforgeExpress({ baseUrl: 'http://localhost:8000', apiKey: '<raw-api-key>' }));
app.get('/demo', (req, res) => res.send('ok'));
app.listen(3000);
```
