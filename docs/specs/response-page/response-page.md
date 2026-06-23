# Response page

User interface: Web page

When the user clicks one of the response buttons, a response page pops up. The first page is aimed to [avoid automated scanners](./scanners.md).

## V1 implementation

The response page V1 implements the Confirmation Page option, thus requiring one extra click to register the answer.

## On answer registration

The act of registration of the answer does not have to be interactive. On the contrary, the fewer clicks are required to register the answer, the better. The ideal amount of clicks required for a registration, is zero.

Once the answer is registrered by the page, the options below are possible.

### Successful answer

The response page displays a thank you message that auto-closes the current browser tab in 8 seconds.

### Duplicate answer error

The response page displays a message explaining that the answer could be registered because previously an answer has already been submitted.

The duplicate answer is checked two times:

- For campaign links, against the registered responses
- For any links, against the deduplication table

Only one answer per `email_id` is allowed, the first answer wins.

Duplicate answer is considered an error, therefore the "successfully registered" logic does not fire, instead the error logic does.

### Other error

The response page displays a message explaining that there has been an error. 

## Fallback answer

In case of an error, the response page offers a fallback "mailto:" link. This link contains the user's (response owner's) email address, response text, subject, and campaign name, so that the respondent can quickly send their reply over email.

## Backend answer processing

Once an answer has been successfully registered, it is processed at the backend according to the campaign rules.

1. If `record_answers` is specified and the campaign is non-empty, the answer gets stored in the Firestore. It can be later accessed through the [campaigns page](../settings/campaigns.md). For clarity, if the campaign is empty (loose buttons), skip Firestore storage.

2. If `forward_answers` is specified OR the campaign is empty (loose buttons), 1CR sends an email via Gmail API to the owner that lists:
- Recipients
- Answer text
- Campaign data if available
- The subject of the original email

The anonymized deduplication record is added in any case with any settings.
