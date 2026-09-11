# Bilingual documentation rules

English | [中文](README.zh.md)

Status: design baseline. These rules govern the repository's English and Chinese technical documents; they do not claim full Markdown or semantic-translation verification.

## Three-file pairing

Each in-scope document is a sibling triple:

- `name.md` is the English document.
- `name.zh.md` is the Chinese document.
- `name.i18n.yaml` records the latest reviewed Git blob hash for both Markdown files.

Both languages carry equal authority. A change to either language requires review of the counterpart and an updated consistency record. The YAML file records blob hashes, not commit hashes and not a translation snapshot.

## Mechanical checks

The local checker validates the rules it claims to cover:

- every in-scope English document has the Chinese document and the YAML record;
- both Markdown files have matching heading, list, table, code-fence, and local-link structure;
- the language switcher after the H1 points to the counterpart;
- local links exist and stay inside the repository;
- the consistency record contains current full Git blob SHA-1 values.

The checker is intentionally a small standard-library subset, not a full Markdown parser. It cannot judge translation quality, terminology, factual equivalence, authorization, or product safety. A green result is mechanical evidence only.

## Review and record workflow

1. Edit the English and Chinese documents together.
2. Run `python3 scripts/check_docs.py` to identify structural or hash drift.
3. Have a human review the meaning, terminology, and naturalness in both languages.
4. Run `python3 scripts/check_docs.py --record path/to/name.md --reviewed` for the explicitly reviewed English paths.
5. Run the checker again and include all three files in the same change.

`--record` requires `--reviewed` and accepts only explicit English Markdown paths. It never serves as a blanket approval for every document.

## Terminology

Use [the terminology list](terminology.md) for stable technical terms. Product language remains subject to review; terms such as “robot interaction memory” and “soul” must not expand the package boundary beyond the contract.
