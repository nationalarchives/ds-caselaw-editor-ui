# QA Playbook for manual PDF uploads

This playbook covers scenarios to test for the manual PDF upload process. These are in addition to routine automated testing.

## Editor can create a stub XML with valid metadata

- Given an editor is signed in
- The editor is able to access the "new stub" form
- The form contains all necessary fields to capture the information needed:
  - Date of submission
  - Name of submitter
  - Email address of submission
  - Date of decision
  - Court code
  - Document title
  - Year
  - Case numbers
  - Claimants
  - Appellants
  - Respondents
  - Defendants
- Submitting the form with valid data creates a new, unpublished stub document with the provided data

## Editor cannot create a stub XML with invalid data

- Given an editor is signed in
- The editor is able to access the "new stub" form
- Submitting the form with missing or invalid data will result in a validation error
  - The following fields are required:
    - Date of submission
    - Name of submitter
    - Email address of submission
    - Date of decision
    - Court code
    - Document title
    - Year
  - Year must be an integer
  - Court code must be a valid [court code](https://github.com/nationalarchives/ds-caselaw-utils/blob/main/courts.md)
- A stub document is not created

## Editor can upload a PDF to a document

- Given an editor is signed in
- The editor is able to access a document's "upload" page
- The editor can select a PDF file to upload
- Uploading the file places the PDF in the expected location
- The PDF can be downloaded via the EUI

## Editor cannot upload any other document type

- Given an editor is signed in
- The editor is able to access a document's "upload" page
- Any attempt to upload a file which is not a PDF will be rejected

## Editor cannot upload a 20MB or larger PDF

- Given an editor is signed in
- The editor is able to access a document's "upload" page
- Any attempt to upload a file which exceeds 20MB will be rejected, regardless of file type

## Only editors can create stub documents

- Given a non-editor user is signed in
- The user is not able to directly access the "new stub" form
- After manually entering the URL, the user is not able to submit the "new stub" form without a validation error
- A stub document is not created

## Only editors can upload PDFs

- Given a non-editor user is signed in
- The user is not able to directly access a document's "upload" page
- After manually entering the URL, the user is not able to upload a file without a validation error
- No changes are made to the document's stored assets
