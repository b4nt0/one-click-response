# Manual button generation

In case the user has access to the web frontend, but not to the Gmail add-on, 1CR implements a fallback manual mode. Using this manual mode, the user can generate the buttons block from the web GUI and manually insert it in their email.

## Input

The manual generation tab works in the same was as the [add button block](../gmail-addon/add-button-block.md) in the Gmail add-on. The difference is that the user has to enter all parameters that are normally picked up from the email:

- Email subject
- Email recipients

All other parameters and warnings must behave exactly the same as they do in the Gmail add-on. The page supports both campaigns and loose buttons.

## Output

The output is a copy-pastable button block that the user can insert in their email in any editor that supports rich text / HTML.

In addition to the raw output, the page contains a quick button to copy the output.