# Dashboard polish preview

Changes: 44-pixel map zoom targets with visible keyboard focus, three-column member cards when the card has at least 800 pixels of width, and compact styling based on card width rather than browser width. Member text columns can shrink without forcing horizontal overflow.

The disposable real-source dashboard now uses a full-width panel and omits the large test-instructions card. Its prior dashboard configuration is backed up in ignored local work storage. Source-test records and deferred departure/return status remain documented separately.

Validation: nine frontend tests passed; formatting passed. Browser checks at 1280 by 900 and 390 by 844 showed wide and stacked member layouts. Away selection showed an empty map while preserving counts; Home restored three positions; Pet-member selection showed one; Everyone restored all three. Zoom controls measured 44 by 44 CSS pixels. Physical touch-display acceptance was not repeated.

The disposable instance loads a separately named local preview card. Published 0.1.0-beta.1 files and production HA are unchanged. This preview is not a new release. Rollback: restore the saved dashboard configuration and remove the preview resource. The original beta resource remains installed.
