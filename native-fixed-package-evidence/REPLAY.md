# Portable independent evidence replay

Use this directory together with the sibling native-fixed-package directory and
.github/workflows/native-fixed-package.yml from this exact retained QA commit.
Keep both artifact ZIPs and both ROOT metadata JSONs separate. The metadata was
collected independently from GitHub and its artifact digest fields were checked
against the downloaded ZIP bytes. Do not regenerate metadata from ZIP contents.

Before executing a retained Python file, verify the SHA-256 of PROTOCOL-FREEZE.json:
ae64ee8724a0883f5bd2e9ae6f8416e235902832f681b9914f96aaa66f4bf138.
Verify every bytes/sha256 entry in its files map. The consumer itself must hash to
d8df410f3c8350a4ee7e8a6404ea12faf49fa4d803d43f15b6c6bbaa3d549ce3.
INPUTS.json binds the source archive, original candidate, inventory and native
harness/workflow. No fixture, Home Assistant or provider module is imported by
the consumer. The replay audits retained public evidence; it does not reexecute
the native test suite.

From the retained commit root, using a standard-library Python runtime:

~~~sh
python3 -I -B native-fixed-package-evidence/independent_package.py \
  --fixture-dir native-fixed-package \
  --workflow .github/workflows/native-fixed-package.yml \
  --artifact-zip native-fixed-package-evidence/artifact.zip \
  --metadata native-fixed-package-evidence/ROOT-METADATA.json \
  --candidate-artifact-zip native-fixed-package-evidence/candidate-artifact.zip \
  --candidate-metadata native-fixed-package-evidence/ROOT-CANDIDATE-METADATA.json \
  --output FRESH-INDEPENDENT-REVIEW.json
~~~

The output path must be fresh. A successful result is byte-identical to
INDEPENDENT-REVIEW.json (SHA-256
42a224af229744c220c0f5145e46896ccfffd73deaa11fb9daa9cfcb7fcbd4a0).
Refusal outputs must be retained separately, never overwritten.
REFUSED-CONSUMER-R1.zip preserves the original before-artifact consumer with its
unchanged protocol and two byte-identical refusals. SCHEMA-AMENDMENT.json and
PEER-AUDIT.json explain why R2 was frozen after inspecting the same artifact
bytes and why its sole schema correction required no native rerun.
