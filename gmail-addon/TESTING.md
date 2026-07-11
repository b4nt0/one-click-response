# Gmail add-on manual testing checklist

## Prerequisites

- Firebase project deployed with hosting and functions
- Script Properties set in Apps Script: `API_BASE_URL`
- User signed in via web settings at least once
- Test campaign with at least two response buttons created

## Compose UI

- [ ] Add-on appears in Gmail compose window
- [ ] Insert button is blocked when no recipients are set
- [ ] Recipient list is displayed when recipients exist
- [ ] Confirmation checkbox is required before insert
- [ ] Warning about copy/paste is visible

## Insert flow

- [ ] Selecting a campaign and inserting adds HTML block to email body
- [ ] Selecting "— Add buttons in-place —" shows caption input field
- [ ] Comma-separated captions create loose buttons in the email body
- [ ] Each button has a unique link with encrypted parameter
- [ ] Campaign with no buttons shows an error notification
- [ ] Empty in-place captions show an error notification

## Response flow

- [ ] Clicking a button opens the confirmation page
- [ ] Confirming registers the response successfully
- [ ] Second click on any button from same email shows duplicate error
- [ ] Recorded response appears in campaign settings (when `record_answers` enabled)
- [ ] Forwarding email sent when `forward_answers` enabled

## Edge cases

- [ ] Changing recipients after insert requires deleting block and re-inserting
- [ ] Key rotation invalidates old links
