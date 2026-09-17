# Watt Workspace Skin Visual Reference Manifest

This directory is the canonical location for exact Human-approved Workspace
Skin visual references used by
[Watt Formal UX/UI — Appearance Architecture & Workspace Skin Library](../../architecture/watt-formal-ui-appearance-and-skin-library.md).

## Status

```text
REFERENCE_IMAGES_IMPORTED
    6

REFERENCE_IMAGES_PENDING
    0

SUBSTITUTE_IMAGES_ALLOWED
    NO

CURRENT_PRODUCTION_SKIN
    01-industrial-cyan.png

FUTURE_EXTERNAL_ASSET_DOGFOOD
    02-executive-amber.png
    03-technical-graphite.png
    04-precision-silver.png
    05-warm-professional.png
    06-futuristic-studio.png
```

The exact selected images provided by the Human are imported under stable
filenames. They must not be replaced with newly generated concepts, stock
images, or visually similar screenshots and still be represented as the same
approved references. A later replacement requires explicit Human approval and
an auditable manifest update.

## Expected assets

| Stable filename | Skin identity | SHA-256 | Status |
|---|---|---|---|
| [01-industrial-cyan.png](01-industrial-cyan.png) | `INDUSTRIAL_CYAN` | `94b18c44c7486fc6528b6d88b461cfd31b9152e2d28049fe6542c9d8285019a6` | `AUTHORITATIVE_VISUAL_TARGET` |
| [02-executive-amber.png](02-executive-amber.png) | `EXECUTIVE_AMBER` | `c5d3b7de7d7752d1a0a75e3072505a58edc067bcce753c62a76110fdb9fa319c` | `FUTURE_EXTERNAL_ASSET_DOGFOOD` |
| [03-technical-graphite.png](03-technical-graphite.png) | `TECHNICAL_GRAPHITE` | `c29ea2ef76a37c76c89f248c92bcf6809d151640a220535d0ad8156e43f8745e` | `FUTURE_EXTERNAL_ASSET_DOGFOOD` |
| [04-precision-silver.png](04-precision-silver.png) | `PRECISION_SILVER` | `431cf7763235afb3e3ac9cee540970239424889b47c7690b781a1ce9d7c31a3c` | `FUTURE_EXTERNAL_ASSET_DOGFOOD` |
| [05-warm-professional.png](05-warm-professional.png) | `WARM_PROFESSIONAL` | `4fc05d7cab65dd04ee0a04b1837239da7362d684c1015733d28af40ea10c56fc` | `FUTURE_EXTERNAL_ASSET_DOGFOOD` |
| [06-futuristic-studio.png](06-futuristic-studio.png) | `FUTURISTIC_STUDIO` | `f363dba5bab8069f85ef7d43df51544da32e0900833873fe96521076e27acae2` | `FUTURE_EXTERNAL_ASSET_DOGFOOD` |

The filenames are canonical and are referenced directly by the appearance
architecture document.

The five deferred references remain approved source assets, but are not current
product options. Their next intended role is to test a future governed flow from
external design source through structured design context, browser render,
visual comparison, iterative correction, and Human acceptance. No ingestion
implementation is authorized by this manifest.
