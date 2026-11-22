# Fonts

English type on the PDF pages:

- Nunito (SIL Open Font License), Copyright 2014 The Nunito Project Authors
- Varela Round (SIL Open Font License), Copyright 2011 The Varela Round Project Authors

Korean type is subset from [Noto Sans KR](https://fonts.google.com/noto/specimen/Noto+Sans+KR)
(SIL Open Font License) at build time. `scripts/build_book.py` downloads the
variable font if `fonts/NotoSansKR-var.ttf` is not already present, then
embeds a subset in the PDFs.

The license text is the SIL Open Font License 1.1:
https://openfontlicense.org
