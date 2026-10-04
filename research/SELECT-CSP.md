# Native select style and the exhibition policy

The iPhone-profile WebKit production check of the pressure study reported a `style-src-attr` violation while constructing its native history selector. The application contained no authored inline style attributes. A diagnostic response with `report-sample` identified the attempted rule as exactly `text-overflow:inherit`. Removing native appearance and disabling format detection did not remove the report.

The policy now permits that single attribute string through its SHA-256 digest:

`style-src-attr 'unsafe-hashes' 'sha256-3oFxofzq3N//6J8H86e9ul4WT2OkJrtonB66gn/TLJw='`

The stylesheet directive remains `style-src 'self'`; there is no general inline-style allowance. Scripts, connections, media and frame restrictions remain as before. A production-response trial produced no policy violation for the native selector, while a separate `color:rgb(1,2,3)` attribute was still blocked and inherited the ordinary page ink instead.

This uses the [CSP Level 3 attribute-hash mechanism](https://www.w3.org/TR/CSP/#unsafe-hashes-usage). The exception is confined to the style-attribute directive; it does not authorize inline scripts or event handlers. The exact browser evidence is preserved in `pressure-csp-diagnosis-001.log` through `003.log`.

The observed engine is the RunPod WebKit test browser with an iPhone 15 profile. This does not claim a physical-device test or that every Safari version exhibits the same behavior.
