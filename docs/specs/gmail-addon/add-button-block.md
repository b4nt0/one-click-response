# Adding a quick response block

To add a quick response block, the user can click the 1CR button in the email compose window.

User interface: Gmail add-on

A dialog pops up that allows the user to:

- Add response buttons by selecting a [campaign](../data-structure.md)
- Add loose response buttons

There's also a hyperlink to the settings page that allows the user to create a new campaign.

The quick response block is added that contains the response buttons that the user has defined.

Each rendered response button contains a hyperlink that leads to the response page. The hyperlink parameter is one encrypted blob that includes:

- campaign identifier (to relate the answer to the campaign it belongs to, empty if the button is loose)
- subject (to relate answers to the email)
- response identifier (to record the answer itself)
- recipients list (to understand how is giving the response and avoid duplication)
- email GUID (to avoid response replay, this identifier is added to the [deduplication](../data-structure.md) record with the `false` value in `response_received` upon insertion)

The encryption happens server-side to avoid partial payload replay or fuzzing attacks that could poison the response database. 

WARNING: Due to unique values baked in the button links, the button block cannot be copied and pasted to other emails. Instead the buttons have to be inserted anew every time - so that the new recipient lists and email identifier can be generated. The warning that explains this, must be present in the Add Response Buttons dialog.

### Replay protection

- Fuzzing is prevented with encryption. An adversary cannot try different response identifiers or recipients without knowing the encryption key. 
- Replay is prevented with campaign and recipients list (for responses associated with a campaign) or with email GUID (for campaignless responses). Duplicate campaign responses from the same recipients do not register. Responses with the same GUID as was used before, do not register.

### More on URL encryption

During registration, every user generates a symmetric key. The key is stored in the [Users entity](../data-structure.md). A user can rotate their key at any time (which would make accepting quick answers to old emails impossible).

The symmetric encryption key is used to pre-encrypt all URL parameters to avoid data poisoning by one of the recipients or a fuzzing actor.

## Recipient list warning

To maintain a true one-click experience, the responses have to take the recipients into account as the person or people who give the answer. Therefore, the recipients will have to be baked into the response hyperlink.

Since at the time of adding responses the email is still being edited, two exceptional situations are possible:

1. The recipients are not yet entered
2. The recipients are changed after the responses are inserted.

To mitigate both risks, the user interface:

- Blocks the insertion button if no recipients are specified, offering an explanation
- Displays the current recipient list and a confirmation box that clarifies that the inserted options will be bound to the recipients as listed

There will be no option to update the recipients list after a change. To accommodate for the new recipients, the user must manually delete the previous response block and add a new one.

## Insertion point

The add-on inserts the response buttons at the current cursor position.

## Order

The buttons must be inserted in the order defined in the campaign.
