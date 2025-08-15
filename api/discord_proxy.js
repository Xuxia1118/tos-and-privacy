export default async function handler(req, res) {
  const targetUrl = `https://discord.com${req.url.replace('/api', '')}`;
  
  try {
    const response = await fetch(targetUrl, {
      method: req.method,
      headers: {
        ...req.headers,
        host: 'discord.com'
      },
      body: req.method !== 'GET' && req.method !== 'HEAD' ? req.body : undefined
    });

    const buffer = await response.arrayBuffer();
    res.status(response.status);
    for (const [key, value] of response.headers.entries()) {
      res.setHeader(key, value);
    }
    res.send(Buffer.from(buffer));
  } catch (err) {
    res.status(500).json({ error: 'Proxy error', details: err.message });
  }
}
