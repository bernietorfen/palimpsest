# Inspecting the standalone drawing

The first two production Chromium audits completed the moving observer's
crossings, keyboard interaction, frozen export, composed passage, mobile
layout and failed-data recovery. Their final assertion caught one stylesheet
policy report. Phase logging located it in the export inspection.

The test parsed the downloaded SVG through `DOMParser` inside the delivered
exhibition page. Chromium applied that page's stylesheet policy to the parsed
SVG's embedded style. A focused diagnostic produced no report during actual
export, screenshots or the accessibility audit; adding only this parsing step
reproduced the violation. Its reported SHA-256 is exactly the digest of the
542,139-byte embedded SVG stylesheet:

`0Uow1cS5juu2dXrAv7kng1WmkyA5kOXRorzNJiZxV00=`

The diagnostic receipt is `origin-csp-002.json`. The browser check now parses
and renders the self-contained downloaded artifact in its own blank document,
with its own error listeners. Main-page errors remain fatal. No application
code, policy header or release artifact was changed to accommodate the test.
The original failed runs and the isolated reproducer remain in the record.
