-- Fixed Window Counter
-- KEYS[1] = counter key
-- ARGV = [limit, window_sec, now_ms, cost?]

local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window_sec = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
if cost == nil then cost = 1 end

-- Compute current window start (seconds)
local now_sec = math.floor(now_ms / 1000)
local window_start = math.floor(now_sec / window_sec) * window_sec

-- Initialize if missing
local exists = redis.call('EXISTS', key)
if exists == 0 then
  redis.call('SET', key, 0, 'EX', window_sec, 'NX')
end

-- Increment by cost
local counter = redis.call('INCRBY', key, cost)

-- Determine allowed/remaining
local allowed = 0
if counter <= limit then allowed = 1 end
local remaining = limit - counter
if remaining < 0 then remaining = 0 end

local reset_at = window_start + window_sec  -- epoch seconds
local retry_after_ms = (reset_at * 1000) - now_ms
if retry_after_ms < 0 then retry_after_ms = 0 end

return { allowed, remaining, limit, reset_at, retry_after_ms }
