-- Atomic Token Bucket using Redis hash
-- KEYS[1] = bucket key
-- ARGV = [capacity, refill_rate_per_sec, now_ms, cost]

local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])

-- Read current state
local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts = tonumber(data[2])

if tokens == nil then tokens = capacity end
if ts == nil then ts = now_ms end

-- Refill tokens
local elapsed_ms = now_ms - ts
if elapsed_ms < 0 then elapsed_ms = 0 end
local elapsed_sec = elapsed_ms / 1000.0
local new_tokens = tokens
if refill and refill > 0 then
  new_tokens = math.min(capacity, tokens + elapsed_sec * refill)
else
  new_tokens = math.min(capacity, tokens)
end

-- Decision
local allowed = 0
if new_tokens >= cost then
  allowed = 1
  new_tokens = new_tokens - cost
end

-- Compute retry_after_ms
local retry_after_ms = 0
if allowed == 0 then
  if refill and refill > 0 then
    local missing = cost - new_tokens
    if missing < 0 then missing = 0 end
    retry_after_ms = math.floor((missing / refill) * 1000.0 + 0.5)
  else
    retry_after_ms = 0
  end
end

-- Persist state
redis.call('HMSET', key, 'tokens', new_tokens, 'ts', now_ms)

-- TTL: approx time to refill full capacity plus buffer
local ttl_sec
if refill and refill > 0 then
  ttl_sec = math.ceil(capacity / refill) + 5
else
  ttl_sec = 3600
end
redis.call('EXPIRE', key, ttl_sec)

-- Return: [allowed, tokens_remaining, capacity, retry_after_ms]
local remaining = math.floor(new_tokens)
return { allowed, remaining, capacity, retry_after_ms }
