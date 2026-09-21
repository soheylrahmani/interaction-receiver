if (!chrome.storage || !chrome.storage.local) {
  alert("chrome.storage API is not available. Please open this popup from the extension icon in Chrome.");
}
function uuidv4() {
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}
function updateDisplay() {
  chrome.storage.local.get(['retail_id', 'session_id', 'client_recommendation'], function(result) {
    document.getElementById('current_retail_id').textContent = result.retail_id || '';
    document.getElementById('current_session_id').textContent = result.session_id || '';
  });
}
document.getElementById('generate').onclick = function() {
  document.getElementById('session_id').value = uuidv4();
};
function updateRecordingStatus() {
  chrome.storage.local.get(['isRecording'], function(result) {
    document.getElementById('recording_status').textContent = result.isRecording ? 'Active' : 'Inactive';
  });
}
document.getElementById('start').onclick = function() {
  const retailId = document.getElementById('retail_id').value;
  const sessionId = document.getElementById('session_id').value;
  const clientRecommendation = document.getElementById('client_recommendation').value;
  chrome.storage.local.set({
    isRecording: true,
    retail_id: retailId,
    session_id: sessionId,
    client_recommendation: clientRecommendation
  }, updateRecordingStatus);
};
document.getElementById('stop').onclick = function() {
  chrome.storage.local.set({ isRecording: false }, updateRecordingStatus);
};
// Load current values
chrome.storage.local.get(['retail_id', 'session_id', 'client_recommendation'], function(result) {
  document.getElementById('retail_id').value = result.retail_id || '';
  document.getElementById('session_id').value = result.session_id || '';
  document.getElementById('client_recommendation').value = result.client_recommendation || '';
  updateDisplay();
  updateRecordingStatus();
}); 