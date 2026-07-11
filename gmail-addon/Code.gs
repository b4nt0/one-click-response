/**
 * One-click Response Gmail add-on.
 *
 * Set Script Properties before deploy:
 *   API_BASE_URL — e.g. https://one-click-response.web.app
 *   FIREBASE_API_KEY — Firebase web API key (for custom token exchange if needed)
 */

var API_BASE_URL = PropertiesService.getScriptProperties().getProperty('API_BASE_URL') || 'http://localhost:5000';

/** Brand title for read-message sidebar and in-product references. */
var ADDON_TITLE = 'One-click Response';

/** Compose sidebar card title (no separate section header). */
var COMPOSE_CARD_TITLE = 'Add response buttons';

/** Sentinel campaign id for comma-separated in-place button captions. */
var IN_PLACE_CAMPAIGN_ID = '__in_place__';

/** Must match oauthScopes in appsscript.json (use action.compose, not message.compose). */
var ADDON_OAUTH_SCOPES = [
  'https://www.googleapis.com/auth/gmail.addons.execute',
  'https://www.googleapis.com/auth/gmail.addons.current.message.metadata',
  'https://www.googleapis.com/auth/gmail.addons.current.action.compose',
  'https://www.googleapis.com/auth/script.external_request',
  'https://www.googleapis.com/auth/userinfo.email',
  'openid',
];

/**
 * One-time installer helper — run from the Apps Script editor, then check Executions logs.
 * Copy the logged client ID into Cloud Functions secret APPS_SCRIPT_OAUTH_CLIENT_ID.
 */
function logOAuthClientId() {
  var token = ScriptApp.getIdentityToken();
  if (!token) {
    Logger.log(
      'No identity token. Add openid to appsscript.json oauthScopes, clasp push, ' +
      'create a test deployment, and run this again from the editor.'
    );
    return;
  }
  var claims = decodeIdentityTokenClaims(token);
  Logger.log('Set APPS_SCRIPT_OAUTH_CLIENT_ID to this exact value:');
  Logger.log(claims.aud || '(aud missing from token)');
  Logger.log('Token email: ' + (claims.email || '(missing)'));
}

/**
 * Compose action entry point (compose window toolbar icon).
 */
function onComposeTrigger(e) {
  return buildComposeCard(e);
}

/**
 * Sidebar when reading an email — directs users to compose.
 */
function onMessageOpen(e) {
  var card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle(ADDON_TITLE))
    .addSection(
      CardService.newCardSection()
        .addWidget(
          CardService.newTextParagraph().setText(
            'To insert response buttons, <b>compose a new email</b> and click the ' +
            '<b>' + ADDON_TITLE + '</b> icon in the compose toolbar (bottom of the draft window).'
          )
        )
        .addWidget(
          CardService.newTextParagraph().setText(
            '<a href="' + API_BASE_URL + '/settings/">Manage campaigns in settings</a>'
          )
        )
    )
    .build();
  return [card];
}

/**
 * Build the compose card UI.
 */
function buildComposeCard(e) {
  var draft = getDraftMetadata(e);
  var recipients = getRecipients(draft);
  var subject = (draft && draft.subject) ? draft.subject : '';

  if (!recipients.length && e.parameters && e.parameters.recipients) {
    recipients = e.parameters.recipients.split(',').filter(function (r) { return r; });
  }
  if (!subject && e.parameters && e.parameters.subject) {
    subject = e.parameters.subject;
  }

  if (!draft && !recipients.length) {
    return CardService.newCardBuilder()
      .setHeader(CardService.newCardHeader().setTitle(COMPOSE_CARD_TITLE))
      .addSection(
        CardService.newCardSection().addWidget(
          CardService.newTextParagraph().setText(
            'Could not read draft metadata. Remove and re-install the add-on test deployment, ' +
            'then approve the requested Gmail permissions when prompted.'
          )
        )
      )
      .build();
  }

  var card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle(COMPOSE_CARD_TITLE));

  var section = CardService.newCardSection();
  var composeRefreshParams = {
    subject: subject,
    recipients: recipients.join(','),
  };

  if (recipients.length === 0) {
    section.addWidget(
      CardService.newTextParagraph().setText(
        'Add at least one recipient before inserting response buttons.'
      )
    );
  } else {
    section.addWidget(
      CardService.newTextParagraph().setText(
        'Recipients: <b>' + recipients.join(', ') + '</b>'
      )
    );

    var selectedCampaignId = (e.formInput && e.formInput.campaignId) || '';
    var campaignInput = buildCampaignDropdown(selectedCampaignId);
    campaignInput.setOnChangeAction(
      CardService.newAction()
        .setFunctionName('onComposeCardRefresh')
        .setParameters(composeRefreshParams)
    );

    var backendAuthUrl = getBackendAuthorizationUrl();
    if (backendAuthUrl) {
      section.addWidget(
        CardService.newTextParagraph().setText(
          'Allow the add-on to contact the ' + ADDON_TITLE + ' backend before loading campaigns.'
        )
      );
      section.addWidget(buildBackendAuthorizationButton(backendAuthUrl));
    } else {
      try {
        var campaigns = fetchCampaigns();
        campaigns.forEach(function (c) {
          campaignInput.addItem(c.name, c.id, c.id === selectedCampaignId);
        });
      } catch (err) {
        if (isUrlFetchPermissionError(err.message || String(err))) {
          var retryAuthUrl = getBackendAuthorizationUrl();
          if (retryAuthUrl) {
            section.addWidget(buildBackendAuthorizationButton(retryAuthUrl));
          }
          section.addWidget(
            CardService.newTextParagraph().setText(
              '<b>Could not load campaigns</b><br>' +
              escapeHtml(err.message || String(err)) +
              '<br><br>Click <b>Connect to backend</b> and approve external requests.'
            )
          );
        } else {
          section.addWidget(
            CardService.newTextParagraph().setText(
              buildAuthFailureHtml(err, err.responseData || null, err.httpCode || null)
            )
          );
        }
      }

      section.addWidget(campaignInput);

      if (selectedCampaignId === '') {
        section.addWidget(buildManageCampaignsLink());
      }

      if (selectedCampaignId === IN_PLACE_CAMPAIGN_ID) {
        section.addWidget(
          CardService.newTextInput()
            .setFieldName('buttonCaptions')
            .setTitle('Button captions')
            .setHint('Comma-separated, e.g. Yes, No, Maybe')
            .setValue((e.formInput && e.formInput.buttonCaptions) || '')
        );
      }
    }

    var confirmChecked = isConfirmRecipientsChecked(e.formInput);
    var confirmInput = CardService.newSelectionInput()
      .setType(CardService.SelectionInputType.CHECK_BOX)
      .setTitle('Confirm recipients')
      .setFieldName('confirmRecipients')
      .addItem('I confirm these recipients are correct', 'yes', confirmChecked);
    confirmInput.setOnChangeAction(
      CardService.newAction()
        .setFunctionName('onComposeCardRefresh')
        .setParameters(composeRefreshParams)
    );
    section.addWidget(confirmInput);

    addPostConfirmWarnings(section, recipients, e.formInput);

    section.addWidget(
      CardService.newTextButton()
        .setText('Insert response block')
        .setOnClickAction(
          CardService.newAction()
            .setFunctionName('insertResponseBlock')
            .setParameters({
              subject: subject,
              recipients: recipients.join(','),
            })
        )
    );
  }

  card.addSection(section);
  return card.build();
}

/**
 * Rebuild compose card when form inputs change (campaign, confirm checkbox, etc.).
 */
function onComposeCardRefresh(e) {
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation().updateCard(buildComposeCard(e)))
    .build();
}

function buildManageCampaignsLink() {
  return CardService.newTextParagraph().setText(
    '<a href="' + API_BASE_URL + '/settings/">Manage campaigns in settings</a>'
  );
}

function isConfirmRecipientsChecked(formInput) {
  if (!formInput || !formInput.confirmRecipients) {
    return false;
  }
  var confirm = formInput.confirmRecipients;
  return (typeof confirm === 'string' ? confirm : confirm.join(',')).indexOf('yes') !== -1;
}

function addPostConfirmWarnings(section, recipients, formInput) {
  if (recipients.length > 1) {
    section.addWidget(
      CardService.newTextParagraph().setText(
        'You are sending to many recipients. They can only give one answer per group, ' +
        'only the first answer will count.'
      )
    );
  }
  if (isConfirmRecipientsChecked(formInput)) {
    section.addWidget(
      CardService.newTextParagraph().setText(
        "Don't copy the response buttons to other emails."
      )
    );
  }
}

function buildCampaignDropdown(selectedCampaignId) {
  return CardService.newSelectionInput()
    .setType(CardService.SelectionInputType.DROPDOWN)
    .setFieldName('campaignId')
    .addItem('— Select campaign —', '', selectedCampaignId === '')
    .addItem('— Add buttons in-place —', IN_PLACE_CAMPAIGN_ID, selectedCampaignId === IN_PLACE_CAMPAIGN_ID);
}

function parseButtonCaptions(raw) {
  if (!raw) {
    return [];
  }
  return raw.split(',').map(function (s) { return s.trim(); }).filter(function (s) { return s; });
}

/**
 * Insert response block into compose body.
 */
function insertResponseBlock(e) {
  requireBackendAccessOrThrow();

  var params = e.parameters;
  var form = e.formInput || {};
  var confirm = form.confirmRecipients;

  if (!confirm || confirm.indexOf('yes') === -1) {
    return notifyCard('Please confirm the recipient list before inserting.');
  }

  var campaignId = form.campaignId;
  if (!campaignId) {
    return notifyCard('Please select a campaign or add buttons in-place.');
  }

  var recipients = (params.recipients || '').split(',').filter(function (r) { return r; });
  if (!recipients.length) {
    return notifyCard('No recipients specified.');
  }

  try {
    var linkButtons;
    if (campaignId === IN_PLACE_CAMPAIGN_ID) {
      var captions = parseButtonCaptions(form.buttonCaptions);
      if (!captions.length) {
        return notifyCard('Enter at least one button caption (comma-separated).');
      }
      linkButtons = captions.map(function (text) {
        return { text: text };
      });
    } else {
      var buttons = fetchCampaignButtons(campaignId);
      if (!buttons.length) {
        return notifyCard('This campaign has no response buttons. Add buttons in settings.');
      }
      linkButtons = buttons.map(function (b) {
        return { response_button_id: b.id };
      });
    }

    var emailId = Utilities.getUuid();
    var payload = {
      subject: params.subject || '',
      recipients: recipients,
      email_id: emailId,
      host_url: API_BASE_URL.replace(/\/$/, ''),
      buttons: linkButtons,
    };

    var result = apiPost('/api/links', payload);
    var html = result.html;

    // Compose UI callbacks return UpdateDraftActionResponse directly (not ActionResponse).
    return CardService.newUpdateDraftActionResponseBuilder()
      .setUpdateDraftBodyAction(
        CardService.newUpdateDraftBodyAction()
          .addUpdateContent(html, CardService.ContentType.MUTABLE_HTML)
          .setUpdateType(CardService.UpdateDraftBodyType.IN_PLACE_INSERT)
      )
      .build();
  } catch (err) {
    return CardService.newActionResponseBuilder()
      .setNotification(
        CardService.newNotification().setText(
          String((err.responseData && err.responseData.error) || err.message || err).substring(0, 250)
        )
      )
      .build();
  }
}

function notifyCard(message) {
  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification().setText(message))
    .build();
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function getDraftMetadata(e) {
  // Compose triggers pass draftMetadata on the event root (not e.gmail.composeMetadata).
  return e.draftMetadata || null;
}

function getRecipients(draftMetadata) {
  var list = [];
  if (!draftMetadata || !draftMetadata.toRecipients) {
    return list;
  }
  draftMetadata.toRecipients.forEach(function (r) {
    var email = typeof r === 'string' ? r : (r && r.emailAddress ? r.emailAddress : '');
    email = email.trim();
    if (email) {
      list.push(email);
    }
  });
  return list;
}

function fetchCampaigns() {
  return apiGet('/api/campaigns');
}

function fetchCampaignButtons(campaignId) {
  return apiGet('/api/campaigns/' + campaignId + '/buttons');
}

function getBackendAuthorizationUrl() {
  // Use the full manifest scope list. Requesting only external_request triggers a
  // Google OAuth bug that asks for invalid gmail.addons.current.message.compose.
  var authInfo = ScriptApp.getAuthorizationInfo(ScriptApp.AuthMode.FULL, ADDON_OAUTH_SCOPES);
  return authInfo.getAuthorizationUrl();
}

function buildBackendAuthorizationButton(authUrl) {
  return CardService.newTextButton()
    .setText('Connect to backend')
    .setAuthorizationAction(
      CardService.newAuthorizationAction().setAuthorizationUrl(authUrl)
    );
}

function requireBackendAccessOrThrow() {
  var authUrl = getBackendAuthorizationUrl();
  if (!authUrl) {
    return;
  }
  CardService.newAuthorizationException()
    .setAuthorizationUrl(authUrl)
    .setResourceDisplayName(ADDON_TITLE + ' backend')
    .throwException();
}

function isUrlFetchPermissionError(message) {
  var text = String(message);
  return text.indexOf('script.external_request') !== -1 ||
    text.indexOf('UrlFetchApp.fetch') !== -1;
}

function apiGet(path) {
  var response = UrlFetchApp.fetch(API_BASE_URL + path, {
    method: 'get',
    headers: authHeaders(),
    muteHttpExceptions: true,
  });
  return handleResponse(response, path);
}

function apiPost(path, body) {
  var response = UrlFetchApp.fetch(API_BASE_URL + path, {
    method: 'post',
    contentType: 'application/json',
    headers: authHeaders(),
    payload: JSON.stringify(body),
    muteHttpExceptions: true,
  });
  return handleResponse(response, path);
}

function authHeaders() {
  var token = ScriptApp.getIdentityToken();
  if (!token) {
    throw new Error(
      'Gmail add-on identity token is unavailable. Re-install the test deployment and approve ' +
      'all permissions (including openid). Signing in at the web settings page does not grant this.'
    );
  }
  logClientAuthDiagnostics(token, 'authHeaders');
  return {
    Authorization: 'Bearer ' + token,
  };
}

function decodeIdentityTokenClaims(token) {
  try {
    var payload = token.split('.')[1];
    var padded = payload;
    while (padded.length % 4 !== 0) {
      padded += '=';
    }
    var json = Utilities.newBlob(Utilities.base64DecodeWebSafe(padded)).getDataAsString();
    return JSON.parse(json);
  } catch (e) {
    return { decode_error: String(e) };
  }
}

function logClientAuthDiagnostics(token, context) {
  var claims = decodeIdentityTokenClaims(token);
  var summary = {
    context: context,
    api_base_url: API_BASE_URL,
    token_length: token ? token.length : 0,
    aud: claims.aud || null,
    email: claims.email || null,
    iss: claims.iss || null,
    exp: claims.exp || null,
    expired: claims.exp ? (claims.exp * 1000 < Date.now()) : null,
  };
  console.log('1CR auth diagnostics: ' + JSON.stringify(summary));
}

function buildClientSideAuthDebugHtml() {
  var token = ScriptApp.getIdentityToken();
  if (!token) {
    return (
      '<b>Add-on token</b><br>' +
      'No identity token from Gmail. Re-install the test deployment and approve openid.'
    );
  }
  var claims = decodeIdentityTokenClaims(token);
  var lines = [
    '<b>Add-on token (from Gmail)</b>',
    'aud (set as backend <code>APPS_SCRIPT_OAUTH_CLIENT_ID</code>): ' +
      '<code>' + escapeHtml(String(claims.aud || '(missing)')) + '</code>',
    'email: ' + escapeHtml(String(claims.email || '(missing)')),
    'iss: ' + escapeHtml(String(claims.iss || '(missing)')),
  ];
  if (claims.exp) {
    var expired = claims.exp * 1000 < Date.now();
    lines.push('expires: ' + (expired ? '<b>EXPIRED</b> — close and re-open the add-on' : 'ok'));
  }
  if (claims.decode_error) {
    lines.push('decode error: ' + escapeHtml(String(claims.decode_error)));
  }
  lines.push(
    '<br><b>Why the backend needs this</b><br>' +
    'The add-on sends a signed Google token proving who you are. The backend must verify ' +
    'that signature and check <code>aud</code> matches <code>APPS_SCRIPT_OAUTH_CLIENT_ID</code> ' +
    'so random callers cannot read your campaigns. This is not a Gmail-side secret — it tells ' +
    'the server which OAuth client issued the token.'
  );
  return lines.join('<br>');
}

function formatAuthDebugHtml(debug) {
  if (!debug) {
    return '';
  }
  var lines = [];
  if (debug.parse_error) {
    lines.push('Backend inspect failed: ' + escapeHtml(String(debug.parse_error).substring(0, 500)));
  }
  if (debug.audience_match_hint) {
    lines.push(escapeHtml(debug.audience_match_hint));
  }
  if (debug.hint) {
    lines.push(escapeHtml(debug.hint));
  }
  if (debug.token_claims) {
    lines.push(
      'Backend saw: aud=' + escapeHtml(String(debug.token_claims.aud || '(missing)')) +
      ', email=' + escapeHtml(String(debug.token_claims.email || '(missing)'))
    );
    if (debug.token_claims.expired === true) {
      lines.push('Token is <b>expired</b>. Re-open the add-on to refresh it.');
    }
  }
  if (debug.configured_secrets) {
    var appsScript = debug.configured_secrets.APPS_SCRIPT_OAUTH_CLIENT_ID || {};
    lines.push(
      'Backend APPS_SCRIPT_OAUTH_CLIENT_ID: ' +
      (appsScript.set ? 'set' : '<b>NOT SET</b>') +
      ' (fingerprint ' + escapeHtml(String(appsScript.fingerprint || '')) + ')'
    );
  }
  if (debug.google_identity_verification_attempts &&
      debug.google_identity_verification_attempts.length) {
    lines.push('Verification attempts:');
    debug.google_identity_verification_attempts.forEach(function (attempt) {
      lines.push(
        '• ' + escapeHtml(attempt.source) + ' ' +
        escapeHtml(attempt.audience_fingerprint || '') + ': ' +
        (attempt.success ? 'OK' : escapeHtml(String(attempt.error || 'failed')))
      );
    });
  }
  if (!lines.length) {
    return '';
  }
  lines.unshift('<b>Backend auth debug</b>');
  return lines.join('<br>');
}

function buildAuthFailureHtml(err, responseData, httpCode) {
  var parts = [
    '<b>Could not load campaigns</b><br>',
    escapeHtml((responseData && responseData.error) || (err && err.message) || String(err)),
  ];
  parts.push('<br><br>' + buildClientSideAuthDebugHtml());
  var backendDebug = formatAuthDebugHtml(responseData && responseData.debug);
  if (backendDebug) {
    parts.push('<br><br>' + backendDebug);
  } else if (httpCode === 401 || (responseData && responseData.code === 'unauthorized')) {
    parts.push(
      '<br><br><i>Backend debug unavailable — redeploy functions (<code>./scripts/deploy.sh</code>) ' +
      'for detailed server-side diagnostics. Compare add-on <code>aud</code> above to your secret.</i>'
    );
  }
  return parts.join('');
}

function fetchAuthInspectReport() {
  var response = UrlFetchApp.fetch(API_BASE_URL + '/api/auth/inspect', {
    method: 'post',
    headers: authHeaders(),
    muteHttpExceptions: true,
  });
  var text = response.getContentText();
  try {
    return JSON.parse(text);
  } catch (e) {
    return { parse_error: text };
  }
}

function makeApiError(message, responseData, httpCode) {
  var err = new Error(message);
  err.responseData = responseData || null;
  err.httpCode = httpCode || null;
  return err;
}

function handleResponse(response, path) {
  var code = response.getResponseCode();
  var text = response.getContentText();
  var data = {};
  try {
    data = JSON.parse(text);
  } catch (e) {
  }
  if (code < 200 || code >= 300) {
    console.log(
      '1CR API error: path=' + path +
      ' status=' + code +
      ' body=' + text.substring(0, 2000)
    );
    var message = data.error || ('HTTP ' + code);
    if (code === 401 || data.code === 'unauthorized') {
      try {
        var inspect = fetchAuthInspectReport();
        if (inspect && !data.debug) {
          data.debug = inspect;
        }
        console.log('1CR auth inspect: ' + JSON.stringify(inspect).substring(0, 3000));
      } catch (inspectErr) {
        console.log('1CR auth inspect failed: ' + inspectErr);
      }
    } else if (data.debug) {
      console.log('1CR auth debug: ' + JSON.stringify(data.debug).substring(0, 3000));
    }
    if (data.code === 'server_misconfigured') {
      message += ' (backend: set APPS_SCRIPT_OAUTH_CLIENT_ID secret and redeploy functions)';
    }
    throw makeApiError(message, data, code);
  }
  return data;
}
