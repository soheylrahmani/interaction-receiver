(function() {
  function getSessionInfo(callback) {
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
      chrome.storage.local.get(['retail_id', 'session_id', 'client_recommendation'], function(result) {
        callback({
          retail_id: result.retail_id,
          session_id: result.session_id,
          client_recommendation: result.client_recommendation
        });
      });
    } else {
      // fallback for non-extension context
      callback({
        retail_id: localStorage.getItem('retail_id'),
        session_id: localStorage.getItem('session_id'),
        client_recommendation: localStorage.getItem('client_recommendation')
      });
    }
  }

  function sendAction(action) {
    getSessionInfo(({ retail_id, session_id, client_recommendation }) => {
      if (!retail_id || !session_id) return;
      if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.get(['isRecording'], function(result) {
          if (!result.isRecording) return;
          fetch('https://your-domain.com/api/v1/interactions/extension-action', {
            method: 'POST',
            body: JSON.stringify({
              retail_id,
              session_id,
              client_recommendation,
              actions: [action],
              url: action.url
            }),
            headers: {'Content-Type': 'application/json'}
          });
        });
      } else {
        // fallback for non-extension context
        if (localStorage.getItem('isRecording') !== 'true') return;
        fetch('https://your-domain.com/api/v1/interactions/extension-action', {
          method: 'POST',
          body: JSON.stringify({
            retail_id,
            session_id,
            client_recommendation,
            actions: [action],
            url: action.url
          }),
          headers: {'Content-Type': 'application/json'}
        });
      }
    });
  }

  document.addEventListener('change', function(e) {
    if (e.target) {
      let selector = '';
      if (e.target.id) selector = '#' + e.target.id;
      else if (e.target.name) selector = '[name="' + e.target.name + '"]';
      else selector = e.target.tagName.toLowerCase();
      let value = e.target.value;
      sendAction({
        type: 'change',
        selector,
        value,
        timestamp: new Date().toISOString(),
        url: window.location.href
      });
    }
  }, true);

  document.addEventListener('click', function(e) {
    if (e.target) {
      let selector = '';
      if (e.target.id) selector = '#' + e.target.id;
      else if (e.target.name) selector = '[name="' + e.target.name + '"]';
      else selector = e.target.tagName.toLowerCase();
      sendAction({
        type: 'click',
        selector,
        value: '',
        timestamp: new Date().toISOString(),
        url: window.location.href
      });
    }
  }, true);
})();