# Avoiding link scanners

Some email servers or clients verify the hyperlinks in the email by loading contents behind the link. It is important that such link loading does not register as an answer.

At the same time, when a real user clicks the link, the act of clicking may be enough to register the answer.

To achieve that, the following automation avoidance techniques are used:

## Confirmation page

This solution requires 1 extra click.

A simple page that renders the response and a confirmation button that the user has to press. While it's not a true 1-click experience, it's the ultimate protection against non-malicious link scanners.

## Zero-click CAPTCHA

This solution requires 0 extra clicks best case and 1 extra click worst case.

[reCAPTCHA v3](https://developers.google.com/recaptcha/docs/v3) is a zero-click CAPTCHA solution that blocks automated bot traffic without interruptions to the user.
