# Model comparison

Latest run per model, same gold set, same prompt, same policy layer.

| Metric | `claude-opus-5` | `claude-sonnet-5` |
| --- | --- | --- |
| Cases × runs | 10 × 3 | 10 × 3 |
| Effort | `medium` | `medium` |
| Overall check accuracy | 98% | 99% |
| Tier exactly right | 93% | 96% |
| Tier within tolerance | 93% | 100% |
| Scope (`ai_in_scope`) | 100% | 100% |
| AI type | 100% | 100% |
| Oversight mode | 100% | 100% |
| Dimension floors met | 100% | 100% |
| Top-10 recall | 100% | 90% |
| Consideration recall | 96% | 93% |
| Tier consistency | 97% | 97% |
| Median latency | 43.0s | 31.9s |
| p95 latency | 63.8s | 46.0s |
| Cost per assessment | $0.1052 | $0.0321 |
| Output tokens (total) | 115,856 | 88,204 |
| API errors | 0 | 0 |

## Where they disagree

Cases where the models returned different tiers.

| Case | `claude-opus-5` | `claude-sonnet-5` |
| --- | --- | --- |
| `underspecified-login-invoice` | medium ×1, high ×2 | medium ×3 |
| `vendor-procurement-copilot` | medium ×3 | medium ×2, high ×1 |
