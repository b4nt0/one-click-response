# One-click response for Gmail

One-click response (hereinafter - 1CR) for Gmail is a tool that adds one or several quick response hyperlinks that allow the email recipient to simply click one of the buttons instead of responding to the email.

The act of clicking the button would:

1. Optionally record the response
2. Optionally send out the response to the original sender

The full product specifications are in [the specs folder](./docs/specs/).

Installation and deployment: [docs/installing](./docs/installing/README.md). Local development: [docs/development](./docs/development/README.md).

The license is [in the LICENSE file](./LICENSE).

## Product components

### Gmail add-on

The Gmail add-on is the email user interface. It allows selecting the campaign and adding the quick response block.

### Web interface

The web interface allows reviewing responses and setting up campaign rules.

### Backend

The backend stores campaigns and responses.
