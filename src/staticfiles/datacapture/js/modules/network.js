(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};

  async function postJson(url, body) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      body,
    });

    let payload = null;
    try {
      payload = await response.json();
    } catch (error) {
      payload = null;
    }

    if (!response.ok) {
      let message = 'Request failed';
      if (payload && Array.isArray(payload.error) && payload.error.length > 0) {
        message = payload.error.join(' ');
      }
      throw new Error(message);
    }

    return payload;
  }

  window.DatacaptureSubjectDetailModules.network = {
    postJson,
  };
})();
