---
name: binance
description: Use binance-cli for Binance Spot, Futures (USD-S), and Convert. Requires auth.
metadata:
  version: 2.1.0
  author: Binance
  openclaw:
    requires:
      bins:
        - binance-cli
    install:
      - kind: shell
        label: Install binance-cli
        script: |
          if npm list -g @binance/binance-cli --depth=0 >/dev/null 2>&1; then
            VERSION="$(binance-cli --version 2>/dev/null | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || true)"
            MAJOR="$(echo "$VERSION" | cut -d. -f1)"

            if [ "$MAJOR" = "1" ]; then
              npm uninstall -g @binance/binance-cli
            fi
          fi

          curl --proto '=https' --tlsv1.2 -LsSf \
            https://github.com/binance/binance-cli/releases/latest/download/binance-cli-installer.sh \
            | sh
license: MIT
---

# Binance

## binance-cli setup

Before using `binance-cli`:

1. If global npm package `@binance/binance-cli` exists and `binance-cli --version` is `< 2.0.0`, uninstall it:

```sh
npm uninstall -g @binance/binance-cli
```

2. Install the latest release:

```sh
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/binance/binance-cli/releases/latest/download/binance-cli-installer.sh \
  | sh
```

3. Verify:

```sh
binance-cli --version
```


> **PREREQUISITE:** Read [`auth.md`](./references/auth.md) for auth, global flags, and security rules.

## Project rules (lost-crypto)

Local additions to the upstream skill. Only the USDS-M Futures references were vendored; the rest of upstream's reference index was dropped on purpose.

- **Demo only.** Create and use profiles with `--env demo` exclusively. The CLI defaults to `prod`, so never run a command without confirming `binance-cli profile view` shows `demo`. Do not create `prod` profiles in this project (max real exposure is 1000 USDT; bots use the API code in `api/`, not this CLI).
- Dev tool, not runtime: use it to inspect positions, balances, funding and klines, and to cross-check paper trading against the exchange.
- Prefer read-only commands. Ask before any order, cancel, leverage or margin change, even on demo.

## Helper Commands

| Command | Description |
|---------|-------------|
| [`futures-usds`](./references/futures-usds.md) | Derivatives Trading (USDS-M Futures) |
| [`futures-usds-streams`](./references/futures-usds-streams.md) | Derivatives Trading Streams (USDS-M Futures) |

## Notes

- ⚠️ **Prod transactions** — always ask user to type `CONFIRM` before executing.
- Use `--help` to get the list of commands and parameters.
- Use the output from both stdout and stderr.
- Append `--profile <name>` to any command to use a non-active profile.
- All authenticated endpoints accept optional `--recvWindow <ms>` (max 60 000).
- Timestamps (`startTime`, `endTime`) are Unix ms.
- For endpoints not listed in the skill, use `binance-cli request (GET|POST|PUT...) <url> [--signed]`. Any Parameters can be added to the request (e.g: `--param1 value --param2 value`).