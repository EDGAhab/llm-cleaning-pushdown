# Pushdownability matrix

Capability: full = runs on storage; partial = split; none = compute fallback.

| plugin        | html_extract | rule_filter | language_id | pii_redact | minhash_sign | exact_dedup |
| ------------- | ------------ | ----------- | ----------- | ---------- | ------------ | ----------- |
| local_sharded | full         | full        | full        | full       | full         | none        |
| base          | none         | full        | full        | full       | full         | none        |
