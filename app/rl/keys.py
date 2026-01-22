def bucket_key(namespace: str, subject: str, name: str) -> str:
    return f"rl:{namespace}:{subject}:{name}"


def window_key(namespace: str, subject: str, window: int) -> str:
    return f"rl:{namespace}:{subject}:win:{window}"


def concurrency_key(namespace: str, subject: str) -> str:
    return f"rl:{namespace}:{subject}:concurrent"


# New helpers for structured LF keys (tenant-aware)
def rl_key_token_bucket(tenant_id: str, subject: str, resource: str) -> str:
    return f"lf:tb:{tenant_id}:{subject}:{resource}"


def rl_key_fixed_window(
    tenant_id: str, subject: str, resource: str, window_epoch: int
) -> str:
    return f"lf:fw:{tenant_id}:{subject}:{resource}:{window_epoch}"


def rl_key_sliding(tenant_id: str, subject: str, resource: str) -> str:
    return f"lf:sw:{tenant_id}:{subject}:{resource}"


def rl_key_conc(tenant_id: str, subject: str, resource: str) -> str:
    return f"lf:cc:{tenant_id}:{subject}:{resource}"
