(function () {
  var base = (window.RAG_API_BASE || '').trim().replace(/\/+$/, '');
  function apiUrl(p) {
    var path = p || '/';
    if (/^https?:\/\//i.test(path)) return path;
    if (path.charAt(0) !== '/') path = '/' + path;
    return base + path;
  }
  function apiFetch(p, opts) {
    return fetch(apiUrl(p), opts || {});
  }
  window.apiUrl = apiUrl;
  window.apiFetch = apiFetch;
})();
