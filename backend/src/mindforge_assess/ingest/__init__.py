"""Offline ingestion: the handbook PDF is read by Claude as a vision-language model.

No local text extraction or OCR happens anywhere in this package. `pdf_slice` uses
pypdf only to *select* pages -- it copies page objects verbatim into a smaller PDF so
that a single request can be aimed at a page range, which the Messages API has no
parameter for. Claude still sees every page as rendered text + image.
"""
